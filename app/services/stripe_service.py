"""
Enhanced Stripe service with improved payment success handling.
"""

import os
import stripe
import logging
from uuid import uuid4
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

from ..core.config import settings

load_dotenv()
logger = logging.getLogger(__name__)


class StripeService:
    """Enhanced service class for Stripe operations."""
    
    def __init__(self):
        # Stripe configuration
        stripe_secret_key = settings.STRIPE_SECRET_KEY
        if not stripe_secret_key:
            logger.warning("Stripe secret key not configured - StripeService will be limited")
            stripe.api_key = None
            self.is_configured = False
        else:
            stripe.api_key = stripe_secret_key
            self.is_configured = True
        stripe.api_version = "2024-06-20"
        
        # Supabase configuration
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Use service role for admin operations
        
        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase configuration not available - database operations will fail")
            self.supabase = None
        else:
            # Initialize Supabase client with service role key for admin operations
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Allowed prices (server trust boundary)
        self.allowed_prices = {
            "pro_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY"),
            "pro_yearly": os.getenv("STRIPE_PRICE_PRO_YEARLY"),
        }
        
        self.enable_automatic_tax = os.getenv("STRIPE_ENABLE_AUTOMATIC_TAX", "false").lower() == "true"
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    def _has_bank_items(self, user_id: str) -> bool:
        try:
            rows = self.supabase.table("bank_items").select("id").eq("user_id", user_id).limit(1).execute()
            return bool(rows.data)
        except Exception:
            return False

    def _apply_pro(self, user_id: str, update_data: Dict[str, Any], email: Optional[str] = None) -> bool:
        result = self.supabase.table("profiles").update(update_data).eq("user_id", user_id).execute()
        if result.data:
            return True
        if not email:
            try:
                info = self.supabase.auth.admin.get_user_by_id(user_id)
                email = info.user.email if info and info.user else None
            except Exception:
                email = None
        inserted = self.supabase.table("profiles").insert({
            "user_id": user_id,
            "email": email or f"{user_id}@unknown.local",
            "has_connected_bank": self._has_bank_items(user_id),
            **update_data,
        }).execute()
        return bool(inserted.data)

    async def _heal_pro_from_stripe(self, user_id: str, profile: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not self.is_configured:
            return None
        profile = profile or {}
        sub = None
        customer_id = profile.get("stripe_customer_id")
        sub_id = profile.get("stripe_subscription_id")
        email = profile.get("email")
        try:
            if sub_id:
                retrieved = stripe.Subscription.retrieve(sub_id)
                if retrieved and retrieved.get("status") in ("active", "trialing"):
                    sub = retrieved
                    customer_id = customer_id or retrieved.get("customer")
            if sub is None and customer_id:
                listed = stripe.Subscription.list(customer=customer_id, status="active", limit=1)
                if listed.data:
                    sub = listed.data[0]
            if sub is None:
                if not email:
                    try:
                        info = self.supabase.auth.admin.get_user_by_id(user_id)
                        email = info.user.email if info and info.user else None
                    except Exception:
                        email = None
                if email:
                    for customer in stripe.Customer.list(email=email, limit=5).data:
                        listed = stripe.Subscription.list(customer=customer.id, status="active", limit=1)
                        if listed.data:
                            sub = listed.data[0]
                            customer_id = customer.id
                            break
        except Exception as e:
            logger.warning(f"Stripe heal lookup failed for {user_id}: {e}")
            return None
        if not sub:
            return None
        update_data = {
            "is_pro": True,
            "stripe_customer_id": customer_id or sub.get("customer"),
            "stripe_subscription_id": sub.get("id"),
            "subscription_status": sub.get("status"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        period_end = sub.get("current_period_end")
        if period_end:
            update_data["subscription_current_period_end"] = datetime.fromtimestamp(
                period_end, tz=timezone.utc
            ).isoformat()
        if not self._apply_pro(user_id, update_data, email=email):
            return None
        return {
            "is_pro": True,
            "subscription_status": sub.get("status"),
            "current_period_end": update_data.get("subscription_current_period_end"),
            "cancel_at_period_end": bool(sub.get("cancel_at_period_end")),
        }
    
    async def create_checkout_session(
        self, 
        plan: str, 
        user_id: str, 
        user_email: str,
        origin: Optional[str] = None,
    ) -> Dict[str, str]:
        """Create a Stripe checkout session."""
        if not stripe.api_key:
            raise Exception("Stripe not configured - check STRIPE_SECRET_KEY environment variable")
        
        price_id = self.allowed_prices.get(plan)
        if not price_id:
            raise ValueError(f"Invalid plan: {plan}")

        frontend_url = settings.resolve_frontend_url(origin)
        logger.info(f"Creating checkout session for user {user_id}, plan {plan}, price {price_id}, return {frontend_url}")
        
        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=f"{frontend_url}/upgrade?success=true&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{frontend_url}/upgrade?canceled=true",
                allow_promotion_codes=True,
                customer_email=user_email,
                metadata={
                    "user_id": str(user_id),
                    "user_email": user_email,
                    "plan": plan
                },
                **({"automatic_tax": {"enabled": True}} if self.enable_automatic_tax else {}),
                idempotency_key=str(uuid4()),
            )
            
            logger.info(f"✅ Checkout session created: {session['id']}")
            return {"sessionId": session["id"], "url": session["url"]}
            
        except stripe.error.StripeError as e:
            logger.error(f"❌ Stripe error creating checkout session: {e}")
            raise Exception(e.user_message or str(e))
        except Exception as e:
            logger.error(f"❌ Error creating checkout session: {e}")
            raise Exception("Failed to create checkout session")
    
    def verify_webhook_signature(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Verify webhook signature and return event."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            logger.info(f"✅ Webhook signature verified for event: {event['type']}")
            return event
        except ValueError as e:
            logger.error(f"❌ Invalid payload: {e}")
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"❌ Invalid signature: {e}")
            raise ValueError("Invalid signature")
    
    async def handle_checkout_completed(self, session: Dict[str, Any]) -> bool:
        """Enhanced payment success handling with comprehensive logging."""
        try:
            session_id = session.get('id')
            metadata = session.get('metadata', {})
            user_id = metadata.get('user_id')
            user_email = metadata.get('user_email')
            plan = metadata.get('plan')
            
            logger.info(f"🎉 Processing payment success for session: {session_id}")
            logger.info(f"User ID: {user_id}, Email: {user_email}, Plan: {plan}")
            
            if not user_id:
                logger.error("❌ No user_id in session metadata")
                return False
            
            # Get the subscription details from Stripe
            subscription_id = session.get('subscription')
            customer_id = session.get('customer')
            
            logger.info(f"Stripe subscription ID: {subscription_id}")
            logger.info(f"Stripe customer ID: {customer_id}")
            
            # Prepare update data
            update_data = {
                'is_pro': True,
                'stripe_customer_id': customer_id,
                'stripe_subscription_id': subscription_id,
                'subscription_status': 'active',
                'subscription_current_period_end': None,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # If we have subscription details, get the period end
            if subscription_id:
                try:
                    subscription = stripe.Subscription.retrieve(subscription_id)
                    period_end = datetime.fromtimestamp(
                        subscription.current_period_end, tz=timezone.utc
                    ).isoformat()
                    update_data['subscription_current_period_end'] = period_end
                    logger.info(f"Subscription period ends: {period_end}")
                except Exception as e:
                    logger.warning(f"Could not retrieve subscription details: {e}")
            
            logger.info(f"Updating profile for user {user_id} with data: {update_data}")
            if not self._apply_pro(user_id, update_data, email=user_email):
                logger.error(f"❌ Failed to apply pro status for user {user_id}")
                return False
            logger.info(f"✅ Successfully upgraded user {user_id} to PRO")
            return True
                
        except Exception as e:
            logger.error(f"❌ Error in payment success handler: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

    async def confirm_checkout_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        session = stripe.checkout.Session.retrieve(session_id)
        status = session.get("status")
        payment_status = session.get("payment_status")
        if status != "complete" and payment_status not in ("paid", "no_payment_required"):
            raise ValueError("Checkout session is not complete")
        metadata = session.get("metadata") or {}
        if str(metadata.get("user_id") or "") != str(user_id):
            raise ValueError("Checkout session does not belong to this user")
        if not await self.handle_checkout_completed(session):
            raise Exception("Failed to apply subscription")
        return await self.get_subscription_status(user_id)
    
    async def handle_subscription_updated(self, subscription: Dict[str, Any]) -> bool:
        """Handle subscription updates with enhanced logging."""
        try:
            subscription_id = subscription['id']
            status_value = subscription['status']
            current_period_end = datetime.fromtimestamp(
                subscription.get('current_period_end', 0), tz=timezone.utc
            ).isoformat()
            
            logger.info(f"📝 Updating subscription {subscription_id} to status: {status_value}")
            
            # Check if subscription is set to cancel at period end
            cancel_at_period_end = subscription.get('cancel_at_period_end', False)
            
            # Determine if user should be pro based on subscription status
            # Keep pro status if subscription is active or trialing, even if set to cancel later
            is_pro = status_value in ['active', 'trialing']
            
            update_data = {
                'subscription_status': status_value,
                'subscription_current_period_end': current_period_end,
                'cancel_at_period_end': cancel_at_period_end,  # Add this line
                'is_pro': is_pro,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table('profiles').update(update_data).eq('stripe_subscription_id', subscription_id).execute()
            
            logger.info(f"Subscription update result: {result}")
            
            if result.data and len(result.data) > 0:
                logger.info(f"✅ Updated subscription status to {status_value} for subscription: {subscription_id}")
                if cancel_at_period_end:
                    logger.info(f"⚠️ Subscription will cancel at period end: {current_period_end}")
                return True
            else:
                logger.error(f"❌ No rows updated for subscription: {subscription_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error handling subscription updated: {e}")
            import traceback
            logger.error(f"Subscription update traceback: {traceback.format_exc()}")
            return False
    
    async def handle_subscription_deleted(self, subscription: Dict[str, Any]) -> bool:
        """Handle subscription cancellation with enhanced logging."""
        try:
            subscription_id = subscription['id']
            
            logger.info(f"🚫 Canceling subscription: {subscription_id}")
            
            update_data = {
                'is_pro': False,
                'subscription_status': 'canceled',
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table('profiles').update(update_data).eq('stripe_subscription_id', subscription_id).execute()
            
            logger.info(f"Subscription cancellation result: {result}")
            
            if result.data and len(result.data) > 0:
                logger.info(f"✅ Canceled pro status for subscription: {subscription_id}")
                return True
            else:
                logger.error(f"❌ No rows updated for subscription cancellation: {subscription_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error handling subscription deleted: {e}")
            import traceback
            logger.error(f"Subscription deletion traceback: {traceback.format_exc()}")
            return False
    
    async def get_subscription_status(self, user_id: str) -> Dict[str, Any]:
        """Get subscription status with period end validation."""
        try:
            logger.info(f"🔍 Checking subscription status for user: {user_id}")
            
            # If Stripe is not configured, return default status
            if not self.is_configured:
                logger.warning("Stripe not configured - returning default subscription status")
                return {"is_pro": False, "cancel_at_period_end": False}
            
            result = (
                self.supabase.table('profiles')
                .select(
                    'email, is_pro, subscription_status, subscription_current_period_end, cancel_at_period_end, stripe_subscription_id, stripe_customer_id'
                )
                .eq('user_id', user_id)
                .limit(1)
                .execute()
            )

            data = result.data[0] if result.data else None
            if not data or not data.get("is_pro"):
                if not data or data.get("stripe_subscription_id") or data.get("stripe_customer_id"):
                    healed = await self._heal_pro_from_stripe(user_id, data)
                    if healed:
                        return healed
            if not data:
                logger.error(f"❌ Profile not found for user: {user_id}")
                return {"is_pro": False, "cancel_at_period_end": False}

            is_pro = data.get('is_pro', False)
            current_period_end = data.get('subscription_current_period_end')
            cancel_at_period_end = data.get('cancel_at_period_end', False)
            subscription_status = data.get('subscription_status')
            
            # Check if subscription has expired
            if is_pro and current_period_end and cancel_at_period_end:
                period_end_date = datetime.fromisoformat(current_period_end.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                
                if now > period_end_date:
                    logger.info(f"⏰ Subscription expired for user {user_id}, removing pro access")
                    
                    # Update database to reflect expired status
                    update_data = {
                        'is_pro': False,
                        'subscription_status': 'expired',
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    self.supabase.table('profiles').update(update_data).eq('user_id', user_id).execute()
                    
                    return {
                        "is_pro": False,
                        "subscription_status": "expired",
                        "current_period_end": current_period_end,
                        "cancel_at_period_end": cancel_at_period_end
                    }
            
            logger.info(f"✅ User {user_id} pro status: {is_pro}")
            
            return {
                "is_pro": is_pro,
                "subscription_status": subscription_status,
                "current_period_end": current_period_end,
                "cancel_at_period_end": cancel_at_period_end
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching subscription status for {user_id}: {e}")
            return {"is_pro": False, "cancel_at_period_end": False}
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile including email with enhanced logging."""
        try:
            logger.info(f"👤 Fetching user profile for: {user_id}")
            
            result = self.supabase.table('profiles').select('email, full_name, is_pro').eq('user_id', user_id).single().execute()
            
            logger.info(f"User profile query result: {result}")
            
            if not result.data:
                logger.error(f"❌ No profile found for user: {user_id}")
                raise Exception("User profile not found")
                
            logger.info(f"✅ Profile found: {result.data}")
            return result.data
            
        except Exception as e:
            logger.error(f"❌ Error fetching user profile: {e}")
            import traceback
            logger.error(f"Get user profile traceback: {traceback.format_exc()}")
            raise Exception("Failed to get user profile")
    
    async def debug_webhook_processing(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Debug method to test webhook processing without actual webhooks."""
        logger.info(f"🧪 Debug processing event: {event_type}")
        logger.info(f"Event data: {event_data}")
        
        try:
            if event_type == 'checkout.session.completed':
                success = await self.handle_checkout_completed(event_data)
                return {"event_type": event_type, "success": success, "message": "Checkout session processed"}
            elif event_type == 'customer.subscription.updated':
                success = await self.handle_subscription_updated(event_data)
                return {"event_type": event_type, "success": success, "message": "Subscription updated"}
            elif event_type == 'customer.subscription.deleted':
                success = await self.handle_subscription_deleted(event_data)
                return {"event_type": event_type, "success": success, "message": "Subscription deleted"}
            else:
                return {"event_type": event_type, "success": False, "message": "Unhandled event type"}
        except Exception as e:
            logger.error(f"❌ Error in debug webhook processing: {e}")
            return {"event_type": event_type, "success": False, "message": str(e)}
        
    async def cancel_subscription(self, user_id: str, cancel_at_period_end: bool = True) -> Dict[str, Any]:
        """Cancel user's subscription."""
        try:
            logger.info(f"🚫 Canceling subscription for user: {user_id}")
            
            # Get user's subscription info
            result = (
                self.supabase.table('profiles')
                .select('stripe_subscription_id, subscription_status')
                .eq('user_id', user_id)
                .single()
                .execute()
            )
            
            if not result.data or not result.data.get('stripe_subscription_id'):
                raise Exception("No active subscription found")
            
            subscription_id = result.data['stripe_subscription_id']
            
            # Cancel the subscription in Stripe
            if cancel_at_period_end:
                # Cancel at period end (user keeps access until billing cycle ends)
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
                logger.info(f"✅ Subscription {subscription_id} will cancel at period end")
            else:
                # Cancel immediately
                subscription = stripe.Subscription.cancel(subscription_id)
                logger.info(f"✅ Subscription {subscription_id} canceled immediately")
            
            # Update database
            update_data = {
                'subscription_status': subscription['status'],
                'cancel_at_period_end': subscription.get('cancel_at_period_end', False),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # If canceled immediately, remove pro status
            if not cancel_at_period_end:
                update_data['is_pro'] = False
            
            self.supabase.table('profiles').update(update_data).eq('user_id', user_id).execute()
            
            return {
                "success": True,
                "message": "Subscription canceled successfully",
                "cancel_at_period_end": cancel_at_period_end
            }
            
        except Exception as e:
            logger.error(f"❌ Error canceling subscription: {e}")
            raise Exception(f"Failed to cancel subscription: {str(e)}")

    async def reactivate_subscription(self, user_id: str) -> Dict[str, Any]:
        """Reactivate a canceled subscription."""
        try:
            logger.info(f"🔄 Reactivating subscription for user: {user_id}")
            
            # Get user's subscription info
            result = (
                self.supabase.table('profiles')
                .select('stripe_subscription_id')
                .eq('user_id', user_id)
                .single()
                .execute()
            )
            
            if not result.data or not result.data.get('stripe_subscription_id'):
                raise Exception("No subscription found")
            
            subscription_id = result.data['stripe_subscription_id']
            
            # Reactivate in Stripe
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=False
            )
            
            # Update database
            update_data = {
                'subscription_status': subscription['status'],
                'cancel_at_period_end': False,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            self.supabase.table('profiles').update(update_data).eq('user_id', user_id).execute()
            
            logger.info(f"✅ Subscription {subscription_id} reactivated")
            
            return {
                "success": True,
                "message": "Subscription reactivated successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Error reactivating subscription: {e}")
            raise Exception(f"Failed to reactivate subscription: {str(e)}")
    
    # Add this method to StripeService
    async def check_expired_subscriptions(self) -> int:
        """Check for and update expired subscriptions."""
        try:
            logger.info("🔍 Checking for expired subscriptions...")
            
            # Get all active pro users with canceled subscriptions
            result = (
                self.supabase.table('profiles')
                .select('user_id, subscription_current_period_end')
                .eq('is_pro', True)
                .eq('cancel_at_period_end', True)
                .not_.is_('subscription_current_period_end', 'null')
                .execute()
            )
            
            if not result.data:
                logger.info("No canceled subscriptions to check")
                return 0
            
            now = datetime.now(timezone.utc)
            expired_count = 0
            
            for profile in result.data:
                user_id = profile['user_id']
                period_end_str = profile['subscription_current_period_end']
                
                try:
                    period_end_date = datetime.fromisoformat(period_end_str.replace('Z', '+00:00'))
                    
                    if now > period_end_date:
                        logger.info(f"⏰ Expiring subscription for user: {user_id}")
                        
                        update_data = {
                            'is_pro': False,
                            'subscription_status': 'expired',
                            'updated_at': now.isoformat()
                        }
                        
                        self.supabase.table('profiles').update(update_data).eq('user_id', user_id).execute()
                        expired_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing expiration for user {user_id}: {e}")
            
            logger.info(f"✅ Expired {expired_count} subscriptions")
            return expired_count
            
        except Exception as e:
            logger.error(f"❌ Error checking expired subscriptions: {e}")
            return 0