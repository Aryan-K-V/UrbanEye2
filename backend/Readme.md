# Civic Issue Detection API with Swagger Documentation

A Flask-based API for detecting civic infrastructure issues using Google Gemini AI, now enhanced with comprehensive Swagger/OpenAPI documentation.

## 🚀 New Features

### Swagger/OpenAPI Documentation
- **Interactive API Documentation**: Access at `/docs/`
- **API Testing Interface**: Test endpoints directly from the browser
- **Auto-generated Documentation**: Complete API specification with request/response models
- **Request Validation**: Automatic validation of API requests
- **Response Marshalling**: Structured and validated API responses

## 📖 API Documentation

### Accessing Swagger UI
Once the server is running, visit:
```
http://localhost:5000/docs/
```

### OpenAPI Specification
The complete API specification is available at:
```
http://localhost:5000/docs/swagger.json
```

## 🔗 API Endpoints

### New Structured API (v1)
All new endpoints are prefixed with `/api/v1` and fully documented in Swagger:

#### Health Check
- **GET** `/api/v1/health` - Check API health status
- **GET** `/api/v1/health/gemini` - Test Gemini AI connection

#### Civic Issue Detection
- **POST** `/api/v1/detection/analyze` - Analyze uploaded image for civic issues
  - Accepts: `image` file in form-data
  - Returns: Detailed analysis with detected issues

#### Categories
- **GET** `/api/v1/categories` - Get all available issue categories

### Legacy Endpoints
The following endpoints remain for backward compatibility:
- **POST** `/report_civic_issue` - Original image analysis endpoint
- **GET** `/health` - Original health check
- **GET** `/test_gemini` - Original Gemini test
- **GET** `/categories` - Original categories endpoint

## 🛠️ Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file with:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Run the Application
```bash
python app.py
```



The API will start on `http://localhost:5000` with Swagger documentation at `/docs/`.

## 📝 API Request Examples

### Using Swagger UI
1. Navigate to `http://localhost:5000/docs/`
2. Expand any endpoint
3. Click "Try it out"
4. Fill in parameters
5. Click "Execute"

### Using cURL

#### Health Check
```bash
curl -X GET "http://localhost:5000/api/v1/health"
```

#### Image Analysis
```bash
curl -X POST "http://localhost:5000/api/v1/detection/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "image=@path/to/your/image.jpg"
```

#### Get Categories
```bash
curl -X GET "http://localhost:5000/api/v1/categories"
```

## 📊 Response Formats

### Successful Detection Response
```json
{
  "success": true,
  "issues_detected": true,
  "issues": [
    {
      "category": "pothole",
      "description": "Large pothole visible on the road surface causing traffic disruption",
      "severity": "high"
    }
  ],
  "count": 1,
  "timestamp": 1642723200,
  "message": "Found 1 civic issue(s)"
}
```

### No Issues Found Response
```json
{
  "success": true,
  "issues_detected": false,
  "message": "No civic issues detected in the image",
  "issues": [],
  "count": 0,
  "timestamp": 1642723200
}
```

### Error Response
```json
{
  "success": false,
  "error": "Invalid file type",
  "message": "Allowed file types: png, jpg, jpeg, gif, bmp, webp"
}
```

## 🎯 Supported Issue Categories

The API can detect the following civic infrastructure issues:

| Category | Description |
|----------|-------------|
| `pothole` | Road surface damage and potholes |
| `garbage` | Waste management issues |
| `sewage` | Sewage overflow and drainage problems |
| `streetlight` | Street lighting issues |
| `infrastructure` | General infrastructure damage |
| `drainage` | Blocked drains and waterlogging |
| `sidewalk` | Damaged sidewalks and footpaths |
| `traffic_signal` | Traffic signal problems |
| `illegal_dumping` | Unauthorized waste disposal |
| `waterlogging` | Water accumulation issues |

## 🔧 Swagger Configuration

### API Information
- **Title**: Civic Issue Detection API
- **Version**: 1.0
- **Description**: AI-powered civic infrastructure issue detection API using Google Gemini
- **Documentation Path**: `/docs/`
- **API Prefix**: `/api/v1`

### Key Features
- **Request Validation**: Automatic validation of file uploads and parameters
- **Response Models**: Structured response models with clear field descriptions
- **Error Handling**: Comprehensive error responses with appropriate HTTP status codes
- **File Upload Support**: Proper handling of multipart/form-data for image uploads
- **CORS Support**: Cross-Origin Resource Sharing enabled for web clients

## 🚀 Deployment

### Using Render (Recommended)
The project includes a `render.yaml` configuration file:

```yaml
services:
  - type: web
    name: flask-backend
    env: python
    plan: free
    buildCommand: ""
    startCommand: gunicorn app:app
```

### Environment Variables for Production
Set the following environment variable in your deployment platform:
- `GEMINI_API_KEY`: Your Google Gemini API key

### Production URL Structure
Once deployed, your API will be available at:
- **Swagger Documentation**: `https://your-domain.com/docs/`
- **API Endpoints**: `https://your-domain.com/api/v1/...`
- **Legacy Endpoints**: `https://your-domain.com/...` (for backward compatibility)

## 🧪 Testing

### Automated Testing via Swagger UI
1. Visit `/docs/`
2. Use the interactive interface to test all endpoints
3. Upload sample images to test the detection functionality
4. Verify response formats and error handling

### Manual Testing with Sample Images
Test the API with various types of images:
- ✅ Road images with potholes
- ✅ Streets with garbage accumulation
- ✅ Broken streetlights
- ✅ Drainage issues
- ✅ Infrastructure damage

### Health Monitoring
- Use `/api/v1/health` for basic health checks
- Use `/api/v1/health/gemini` to verify AI service connectivity
- Monitor response times and error rates

## 📱 Client Integration

### Flutter/Mobile Apps
The API maintains backward compatibility with existing Flutter applications while providing new structured endpoints for enhanced functionality.

### Web Applications
Use the new `/api/v1/` endpoints for better structure and documentation. The Swagger UI can serve as a reference for frontend developers.

### Third-party Integrations
The OpenAPI specification at `/docs/swagger.json` can be used to generate client SDKs for various programming languages.

## 🔍 Monitoring & Analytics

The project includes monitoring capabilities:
- **Real-time Status**: Check API availability
- **Analytics Dashboard**: Track usage statistics
- **Response Time Monitoring**: Monitor performance metrics
- **Error Tracking**: Log and analyze failures

Access the monitoring dashboard at:
```
http://localhost:5000/docs/monitoring.html
```

## 🛡️ Security Considerations

### File Upload Security
- File type validation (only image formats allowed)
- File size limits (16MB maximum)
- Content validation to ensure uploaded files are valid images

### API Security
- Input validation on all endpoints
- Proper error handling without exposing sensitive information
- CORS configuration for controlled access

### Production Recommendations
- Use HTTPS in production
- Implement rate limiting
- Add authentication for sensitive operations
- Monitor API usage and implement logging

## 🤝 Contributing

### Adding New Endpoints
1. Define the resource class inheriting from `Resource`
2. Add appropriate decorators (`@api.doc`, `@api.marshal_with`, etc.)
3. Define request/response models using `api.model`
4. Add comprehensive documentation strings

### Example New Endpoint
```python
@api.route('/new-endpoint')
class NewEndpoint(Resource):
    @api.doc('new_endpoint_description')
    @api.marshal_with(response_model)
    @api.response(200, 'Success')
    @api.response(400, 'Bad Request', error_response)
    def get(self):
        """Endpoint description for Swagger"""
        return {"message": "Hello World"}, 200
```

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the Swagger documentation at `/docs/`
2. Review the API response models and error messages
3. Test endpoints using the interactive Swagger UI
4. Check logs for detailed error information

## 🔄 Migration Guide

### From Legacy to New API
If you're using the legacy endpoints, consider migrating to the new structured API:

| Legacy Endpoint | New Endpoint | Benefits |
|----------------|--------------|----------|
| `POST /report_civic_issue` | `POST /api/v1/detection/analyze` | Better documentation, validation |
| `GET /health` | `GET /api/v1/health` | Structured response, monitoring |
| `GET /test_gemini` | `GET /api/v1/health/gemini` | Consistent naming, better docs |
| `GET /categories` | `GET /api/v1/categories` | Versioned, future-proof |

### Breaking Changes
None - all legacy endpoints remain functional for backward compatibility.
