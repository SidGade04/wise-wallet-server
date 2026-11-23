# settings_service.py - Updated with GET methods
import os
from datetime import datetime
import io
import csv
import zipfile
import stripe
import json
import logging
from typing import Iterable, Dict, Any
from supabase import create_client, Client
from ..core.config import settings

logger = logging.getLogger(__name__)
_supabase_url = os.getenv("SUPABASE_URL")
_supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = (
    create_client(_supabase_url, _supabase_key)
    if _supabase_url and _supabase_key
    else None
)

class SettingsService:
    """
    Consolidated service for profile, notifications, preferences, billing portal,
    data export, and account deletion.
    """

    def __init__(self):
        # Supabase
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("Missing Supabase configuration")
        self.db: Client = create_client(url, key)

        # Stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe.api_version = "2024-06-20"

    # ----------------- Profile -----------------
    async def get_profile(self, user_id: str):
        try:
            res = self.db.table("profiles").select(
                "id,email,full_name,notif_email_weekly,notif_inapp_alerts,pref_theme,pref_currency,pref_timezone"
            ).eq("user_id", user_id).single().execute()
            
            if not res.data:
                raise ValueError("Profile not found")
            
            return res.data
        except Exception as e:
            logger.error(f"Database error getting profile {user_id}: {str(e)}")
            raise ValueError("Failed to retrieve profile")

    async def update_profile(self, user_id: str, full_name: str, email: str):
        try:
            # Basic email validation
            if not email or "@" not in email:
                raise ValueError("Invalid email format")
            
            res = self.db.table("profiles").update({
                "full_name": full_name, 
                "email": email,
                "updated_at": "now()"
            }).eq("user_id", user_id).execute()
            
            if not res.data:
                raise ValueError("Profile update failed - no rows updated")
            
            logger.info(f"Profile updated for user {user_id}")
            return res.data[0]
        except Exception as e:
            logger.error(f"Failed to update profile {user_id}: {str(e)}")
            raise ValueError(f"Profile update failed: {str(e)}")

    # ----------------- Notifications -----------------
    async def get_notifications(self, user_id: str):
        """Get notification settings for a user"""
        try:
            res = self.db.table("profiles").select(
                "notif_email_weekly,notif_inapp_alerts"
            ).eq("user_id", user_id).single().execute()
            
            if not res.data:
                raise ValueError("User not found")
            
            return {
                "emailWeekly": res.data.get("notif_email_weekly", True),
                "inAppAlerts": res.data.get("notif_inapp_alerts", True)
            }
        except Exception as e:
            logger.error(f"Failed to get notifications for user {user_id}: {str(e)}")
            raise ValueError("Failed to retrieve notification settings")

    async def update_notifications(self, user_id: str, email_weekly: bool, in_app_alerts: bool):
        try:
            res = self.db.table("profiles").update({
                "notif_email_weekly": email_weekly,
                "notif_inapp_alerts": in_app_alerts,
                "updated_at": "now()"
            }).eq("user_id", user_id).execute()
            
            if not res.data:
                raise ValueError("Notification update failed - no rows updated")
            
            logger.info(f"Notifications updated for user {user_id}")
            return res.data[0]
        except Exception as e:
            logger.error(f"Failed to update notifications {user_id}: {str(e)}")
            raise ValueError(f"Notification update failed: {str(e)}")

    # ----------------- Preferences -----------------
    async def get_preferences(self, user_id: str):
        try:
            res = (
                self.db.table("profiles")
                .select("pref_theme,pref_currency,pref_timezone")
                .eq("user_id", user_id)   # ← was id
                .single()
                .execute()
            )
            data = res.data or {}
            return {
                "theme": data.get("pref_theme", "system"),
                "currency": data.get("pref_currency", "USD"),
                "timezone": data.get("pref_timezone", "America/Chicago"),
            }
        except Exception as e:
            logger.error(f"Failed to get preferences for user {user_id}: {e}")
            raise ValueError("Failed to retrieve preferences")


    async def update_preferences(self, user_id: str, email: str | None, theme: str, currency: str, timezone: str):
        try:
            # 1) Try update existing row
            upd = (
                self.db.table("profiles")
                .update({"pref_theme": theme, "pref_currency": currency, "pref_timezone": timezone})
                .eq("user_id", user_id)
                .execute()
            )
            updated_any = bool(upd.data) and len(upd.data) > 0

            # 2) If no row, insert (must include NOT NULL columns like email)
            if not updated_any:
                if not email:
                    raise ValueError("Cannot create profile row: email is required but missing")
                self.db.table("profiles").insert({
                    "user_id": user_id,
                    "email": email,  # satisfy NOT NULL constraint
                    "pref_theme": theme,
                    "pref_currency": currency,
                    "pref_timezone": timezone,
                }).execute()

            # 3) Read back
            res = (
                self.db.table("profiles")
                .select("pref_theme,pref_currency,pref_timezone")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            return res.data
        except Exception as e:
            logger.error(f"Failed to update preferences {user_id}: {e}")
            raise ValueError(str(e))


    # ----------------- Billing Portal -----------------
    async def create_billing_portal(self, user_id: str) -> str:
        try:
            # Try to fetch stripe_customer_id from profiles
            try:
                row = self.db.table("profiles").select("stripe_customer_id").eq("user_id", user_id).single().execute().data
                customer_id = row and row.get("stripe_customer_id") if row else None
            except Exception as e:
                logger.warning(f"Could not fetch stripe_customer_id for user {user_id}: {str(e)}")
                customer_id = None
            
            if not customer_id:
                # If no customer_id found, check if we can get it from Stripe directly
                # This is a fallback - you might need to create the customer first
                logger.error(f"No Stripe customer ID found for user {user_id}")
                raise ValueError("No billing account found. Please contact support.")
            
            # Create the billing portal session
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=f"{settings.FRONTEND_URL}/settings"
            )
            
            logger.info(f"Billing portal session created for user {user_id}")
            return session["url"]
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating billing portal for user {user_id}: {str(e)}")
            raise ValueError(f"Billing portal error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create billing portal for user {user_id}: {str(e)}")
            raise ValueError(f"Billing portal creation failed: {str(e)}")

    # ----------------- Data Export -----------------
    def _as_csv_bytes(self, rows: Iterable[Dict[str, Any]], headers: list[str]) -> bytes:
        """Convert rows to CSV bytes"""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r or {})
        return buf.getvalue().encode("utf-8")

    async def export_user_zip(self, user_id: str) -> bytes:
        try:
            export_data = {
                "export_info": {
                    "exported_at": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                    "version": "1.0"
                }
            }
            
            # Helper function to safely query tables
            def safe_table_query(table_name: str):
                try:
                    result = self.db.table(table_name).select('*').eq('user_id', user_id).execute()
                    return result.data or []
                except Exception as e:
                    logger.warning(f"Table {table_name} not accessible: {str(e)}")
                    return []
            
            # Query the tables that actually exist based on your schema
            export_data["profile"] = safe_table_query('profiles')
            export_data["transactions"] = safe_table_query('transactions')
            export_data["accounts"] = safe_table_query('accounts')
            export_data["bank_items"] = safe_table_query('bank_items')
            
            # Add any other tables you might have
            export_data["budgets"] = safe_table_query('budgets')
            export_data["goals"] = safe_table_query('goals')
            
            # For profile, get first item if exists (should be single record per user)
            if export_data["profile"]:
                export_data["profile"] = export_data["profile"][0]
            else:
                export_data["profile"] = None
            
            # Extract unique categories from transactions for reference
            categories_set = set()
            for transaction in export_data["transactions"]:
                if transaction.get("category"):
                    # category is JSONB, could be array or object
                    category_data = transaction["category"]
                    if isinstance(category_data, list):
                        categories_set.update(category_data)
                    elif isinstance(category_data, str):
                        categories_set.add(category_data)
                    elif isinstance(category_data, dict):
                        # If category is an object, add its string representation or specific fields
                        categories_set.add(str(category_data))
            
            export_data["categories_used"] = sorted(list(categories_set))
            
            # Create ZIP file
            import io
            import zipfile
            import json
            from datetime import datetime
            
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add each data type as a JSON file
                for data_type, data in export_data.items():
                    if data_type != "export_info":
                        zip_file.writestr(f'{data_type}.json', json.dumps(data, indent=2, default=str))
                
                # Add export info
                zip_file.writestr('export_info.json', json.dumps(export_data["export_info"], indent=2))
                
                # Create comprehensive README
                transaction_count = len(export_data["transactions"])
                account_count = len(export_data["accounts"])
                categories_count = len(export_data["categories_used"])
                
                readme_content = f"""Wise Wallet Data Export

                    Export Details:
                    - Exported on: {export_data["export_info"]["exported_at"]}
                    - User ID: {user_id}
                    - Export Version: {export_data["export_info"]["version"]}

                    Data Summary:
                    - Transactions: {transaction_count} records
                    - Accounts: {account_count} records
                    - Bank Items: {len(export_data["bank_items"])} records
                    - Categories Used: {categories_count} unique categories
                    - Profile: {'Yes' if export_data["profile"] else 'No profile data'}

                    Files Included:
                    - export_info.json: Export metadata
                    - profile.json: Your account profile information
                    - transactions.json: All transaction data with amounts, dates, merchants, categories
                    - accounts.json: Your connected accounts
                    - bank_items.json: Bank connection items
                    - categories_used.json: List of all categories found in your transactions
                    - budgets.json: Your budget data (if any)
                    - goals.json: Your financial goals (if any)

                    Transaction Data Notes:
                    - Categories are stored as JSONB within each transaction
                    - Amount values are in the currency specified (default: USD)
                    - Dates are in YYYY-MM-DD format
                    - Pending transactions are marked with the 'pending' field

                    Status:
                    {'This appears to be a new account with no transactions yet.' if transaction_count == 0 else f'Export completed successfully with {transaction_count} transactions across {account_count} accounts.'}

                    Data Format:
                    All data is exported as JSON files. Transaction amounts are numeric values.
                    Category data is preserved exactly as stored in the database (JSONB format).
                    """
                                
                zip_file.writestr('README.txt', readme_content)
            
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Export failed for user {user_id}: {str(e)}")
            raise Exception(f"Failed to export data: {str(e)}")


    # ----------------- Account Deletion -----------------
    async def delete_account(self, user_id: str):
        """Delete user account and all associated data"""
        try:
            # Delete child data first if FK constraints exist
            self.db.table("transactions").delete().eq("user_id", user_id).execute()
            self.db.table("subscriptions").delete().eq("user_id", user_id).execute()
            self.db.table("investments").delete().eq("user_id", user_id).execute()
            
            # Delete profile last
            profile_result = self.db.table("profiles").delete().eq("user_id", user_id).execute()
            
            # Optional: remove auth user (if client supports admin)
            try:
                self.db.auth.admin.delete_user(user_id)  # type: ignore[attr-defined]
            except Exception as e:
                logger.warning(f"Failed to delete auth user {user_id}: {str(e)}")
            
            logger.info(f"Account deleted for user {user_id}")
            return {"ok": True, "message": "Account deleted successfully"}
        except Exception as e:
            logger.error(f"Failed to delete account for user {user_id}: {str(e)}")
            raise ValueError(f"Account deletion failed: {str(e)}")
        
        # Add these methods to your SettingsService class

    async def get_notifications(self, user_id: str):
        """Get notification settings - return defaults for now"""
        try:
            return {
                "emailWeekly": True,
                "inAppAlerts": True
            }
        except Exception as e:
            logger.error(f"Failed to get notifications for user {user_id}: {str(e)}")
            raise ValueError("Failed to retrieve notification settings")

    async def get_preferences(self, user_id: str):
        """Get preferences - return defaults for now"""
        try:
            return {
                "theme": "system",
                "currency": "USD", 
                "timezone": "America/Chicago"
            }
        except Exception as e:
            logger.error(f"Failed to get preferences for user {user_id}: {str(e)}")
            raise ValueError("Failed to retrieve preferences")
