# Wise Wallet - Server

A robust Python backend API for the Wise Wallet financial management application, providing secure financial data processing, AI-powered insights, and third-party integrations.

## 🚀 Features

- **RESTful API**: FastAPI-based API with automatic documentation
- **Bank Integration**: Plaid API integration for secure banking data
- **Payment Processing**: Stripe integration for subscriptions and payments
- **Database Management**: SQLAlchemy ORM with PostgreSQL/Supabase
- **Authentication**: JWT-based authentication with Supabase
- **Real-time Updates**: WebSocket support for live data updates
- **Safety & Compliance**: Financial data validation and security measures

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (via Supabase)
- **ORM**: SQLAlchemy
- **Authentication**: JWT + Supabase Auth
- **Banking API**: Plaid
- **Payment Processing**: Stripe
- **Testing**: pytest
- **Documentation**: OpenAPI/Swagger

## 📦 Installation

1. **Clone the repository and navigate to server directory**:
   ```bash
   cd server
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the server directory:
   ```env
   # Database
   DATABASE_URL=your_supabase_database_url
   
   # Authentication
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_service_key
   JWT_SECRET=your_jwt_secret
   
   # Plaid Configuration
   PLAID_CLIENT_ID=your_plaid_client_id
   PLAID_SECRET=your_plaid_secret
   PLAID_ENV=sandbox  # or development/production
   
   # Stripe Configuration
   STRIPE_SECRET_KEY=your_stripe_secret_key
   STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
   
   
   
   # Server Configuration
   HOST=0.0.0.0
   PORT=8000
   DEBUG=True
   ```

5. **Run database migrations**:
   ```bash
   # If using Alembic
   alembic upgrade head
   ```

6. **Start the development server**:
   ```bash
   python main.py
   # or
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the API documentation**:
   Navigate to `http://localhost:8000/docs`

## 🏗️ Project Structure

```
server/
├── app/
│   ├── core/               # Core application configuration
│   │   ├── auth.py         # Authentication utilities
│   │   └── config.py       # Application configuration
│   ├── models/             # Database models
│   │   ├── plaid_models.py
│   │   ├── safety_models.py
│   │   ├── schemas.py
│   │   ├── settings_models.py
│   │   └── stripe_models.py
│   ├── routes/             # API route handlers
│   │   ├── plaid_routes.py # Plaid integration endpoints
│   │   ├── settings_routes.py
│   │   └── stripe_routes.py
│   └── services/           # Business logic services
│       ├── budget_service.py
│       ├── db.py           # Database utilities
│       ├── plaid_service.py
│       ├── safety_service.py
│       ├── settings_service.py
│       └── stripe_service.py
├── main.py                 # Application entry point
└── requirements.txt       # Python dependencies
```

## 🎨 Available Scripts

- `python main.py` - Start the development server
- `uvicorn main:app --reload` - Start with auto-reload
- `pytest` - Run tests
- `pytest --cov=app` - Run tests with coverage
- `alembic upgrade head` - Apply database migrations
- `alembic revision --autogenerate -m "description"` - Generate migration

## 🔧 Configuration

### Environment Variables
All configuration is handled through environment variables. See the installation section for required variables.

### Database Configuration
The application uses SQLAlchemy with PostgreSQL. Database URL should be provided via `DATABASE_URL` environment variable.



## 🔌 API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/refresh` - Refresh JWT token



### Plaid Integration
- `POST /plaid/link` - Create Plaid link token
- `POST /plaid/exchange` - Exchange public token
- `GET /plaid/accounts` - Get linked accounts
- `GET /plaid/transactions` - Get transactions

### Stripe Integration
- `POST /stripe/create-checkout` - Create checkout session
- `POST /stripe/webhook` - Handle Stripe webhooks
- `GET /stripe/subscriptions` - Get user subscriptions

### Settings
- `GET /settings` - Get user settings
- `PUT /settings` - Update user settings

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_ai_routes.py

# Run tests in watch mode
pytest-watch
```

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Input Validation**: Pydantic models for request validation
- **Rate Limiting**: API rate limiting to prevent abuse
- **CORS Configuration**: Cross-origin resource sharing setup
- **Data Encryption**: Sensitive data encryption at rest
- **Audit Logging**: Comprehensive logging for security events

## 📊 Monitoring & Logging

- **Structured Logging**: JSON-formatted logs for easy parsing
- **Error Tracking**: Comprehensive error handling and reporting
- **Performance Monitoring**: Request timing and performance metrics
- **Health Checks**: `/health` endpoint for monitoring

## 🚀 Deployment

### Docker Deployment
```bash
# Build the image
docker build -t wise-wallet-server .

# Run the container
docker run -p 8000:8000 --env-file .env wise-wallet-server
```

### Production Deployment
1. **Set up production environment**:
   - Use production database (PostgreSQL)
   - Configure production environment variables
   - Set up SSL certificates

2. **Deploy with Gunicorn**:
   ```bash
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

3. **Set up reverse proxy** (Nginx recommended):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Install development dependencies: `pip install -r requirements-dev.txt`
4. Make your changes and add tests
5. Run tests: `pytest`
6. Commit your changes: `git commit -m 'Add amazing feature'`
7. Push to the branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the API documentation at `/docs`
- Review the troubleshooting guide

## 🔗 Related Links

- [Frontend Documentation](../client/README.md)
- [Project Documentation](../README.md)
- [API Documentation](http://localhost:8000/docs)
