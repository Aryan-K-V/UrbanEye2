import os
import io
import base64
from flask import Flask, request
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from PIL import Image
import google.generativeai as genai
from flask_cors import CORS
from flask_restx import Api, Resource, fields, reqparse
import logging
import time
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=['*'])  # Enable CORS for Flutter app integration

# Flask-RESTX API Setup
api = Api(
    app,
    version='1.0',
    title='Civic Issue Detection API',
    description='AI-powered civic infrastructure issue detection API using Google Gemini',
    doc='/docs/',  # Swagger UI will be available at /docs/
    prefix='/api/v1'
)

# Define namespaces
health_ns = api.namespace('health', description='Health check operations')
detection_ns = api.namespace('detection', description='Civic issue detection operations')
categories_ns = api.namespace('categories', description='Issue category operations')

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

from dotenv import load_dotenv
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model
model = genai.GenerativeModel('gemini-2.5-flash')

# Define API models for documentation
health_response = api.model('HealthResponse', {
    'status': fields.String(required=True, description='API status', example='healthy'),
    'message': fields.String(required=True, description='Status message', example='Civic Issue Detection API is running'),
    'timestamp': fields.Integer(required=True, description='Unix timestamp', example=1642723200)
})

gemini_test_response = api.model('GeminiTestResponse', {
    'status': fields.String(required=True, description='Test status', example='success'),
    'message': fields.String(required=True, description='Test message', example='Gemini API is working'),
    'response': fields.String(required=True, description='Gemini response', example='Hello from Gemini!'),
    'timestamp': fields.Integer(required=True, description='Unix timestamp', example=1642723200)
})

issue_detail = api.model('IssueDetail', {
    'category': fields.String(required=True, description='Issue category', 
                             example='pothole', 
                             enum=['pothole', 'garbage', 'sewage', 'infrastructure', 'drainage', 
                                   'streetlight', 'sidewalk', 'traffic_signal', 'illegal_dumping', 'waterlogging']),
    'description': fields.String(required=True, description='Detailed description of the issue', 
                                example='Large pothole visible on the road surface causing traffic disruption'),
    'severity': fields.String(required=True, description='Issue severity level', 
                             example='high', enum=['low', 'medium', 'high'])
})

detection_response = api.model('DetectionResponse', {
    'success': fields.Boolean(required=True, description='Request success status', example=True),
    'issues_detected': fields.Boolean(required=True, description='Whether issues were found', example=True),
    'issues': fields.List(fields.Nested(issue_detail), description='List of detected issues'),
    'count': fields.Integer(required=True, description='Number of issues found', example=2),
    'timestamp': fields.Integer(required=True, description='Unix timestamp', example=1642723200),
    'message': fields.String(required=True, description='Response message', example='Found 2 civic issue(s)')
})

category_item = api.model('CategoryItem', {
    'id': fields.String(required=True, description='Category ID', example='pothole'),
    'name': fields.String(required=True, description='Category display name', example='Pothole'),
    'description': fields.String(required=True, description='Category description', 
                                example='Road surface damage and potholes')
})

categories_response = api.model('CategoriesResponse', {
    'success': fields.Boolean(required=True, description='Request success status', example=True),
    'categories': fields.List(fields.Nested(category_item), description='List of available categories'),
    'count': fields.Integer(required=True, description='Number of categories', example=10)
})

error_response = api.model('ErrorResponse', {
    'success': fields.Boolean(required=True, description='Request success status', example=False),
    'error': fields.String(required=True, description='Error type', example='Invalid file type'),
    'message': fields.String(required=True, description='Error message', 
                           example='Allowed file types: png, jpg, jpeg, gif, bmp, webp'),
    'debug_info': fields.String(required=False, description='Debug information (only in debug mode)')
})

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image_with_gemini(image_data):
    """Process image with Gemini API to detect civic issues"""
    try:
        # Create PIL Image from bytes
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Enhanced prompt for better civic issue detection
        prompt = """
        You are an AI assistant specialized in detecting civic infrastructure issues. 
        Analyze this image carefully and look for these specific civic problems:

        1. ROAD ISSUES: Potholes, cracks, damaged asphalt, road surface problems
        2. WASTE MANAGEMENT: Garbage accumulation, overflowing bins, illegal dumping, littering
        3. WATER/SEWAGE: Sewage overflows, drainage blockages, water leakage, flooding
        4. INFRASTRUCTURE: Broken streetlights, damaged sidewalks, faulty traffic signals
        5. PUBLIC PROPERTY: Damaged benches, broken signage, vandalism

        If you detect ANY civic issues, respond with this EXACT JSON format:
        {
            "issues_found": true,
            "issues": [
                {
                    "category": "one of: pothole, garbage, sewage, infrastructure, drainage, streetlight, sidewalk, traffic_signal, illegal_dumping, waterlogging",
                    "description": "Clear, detailed description of what you see (2-3 sentences)",
                    "severity": "low, medium, or high"
                }
            ]
        }

        If NO civic issues are detected, respond with:
        {
            "issues_found": false,
            "message": "No civic issues detected in the image"
        }

        IMPORTANT: 
        - Only respond with valid JSON
        - Be specific about what you see
        - Focus only on civic infrastructure problems
        - Ignore people, vehicles, or private property unless they're causing civic issues
        """
        
        # Generate response from Gemini
        response = model.generate_content([prompt, image])
        response_text = response.text.strip()
        
        logger.info(f"Gemini raw response: {response_text}")
        
        # Clean and parse JSON response
        try:
            # Remove any markdown formatting
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            # Find JSON content
            if '{' in response_text and '}' in response_text:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_str = response_text[json_start:json_end]
                
                result = json.loads(json_str)
                
                # Validate response structure
                if 'issues_found' not in result:
                    raise ValueError("Invalid response format")
                
                return result
            else:
                # Fallback: create response based on keywords
                civic_keywords = ['pothole', 'garbage', 'waste', 'sewage', 'drain', 
                                'street', 'light', 'road', 'damage', 'broken', 'overflow']
                
                if any(keyword in response_text.lower() for keyword in civic_keywords):
                    return {
                        "issues_found": True,
                        "issues": [
                            {
                                "category": "general",
                                "description": response_text[:200] + "..." if len(response_text) > 200 else response_text,
                                "severity": "medium"
                            }
                        ]
                    }
                else:
                    return {
                        "issues_found": False,
                        "message": "No civic issues detected in the image"
                    }
                    
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Response text: {response_text}")
            
            # Fallback response
            return {
                "issues_found": False,
                "message": "No civic issues detected in the image",
                "debug_info": f"JSON parse error: {str(e)}"
            }
                
    except Exception as e:
        logger.error(f"Error processing image with Gemini: {str(e)}")
        raise

# Health Check Endpoints
@health_ns.route('')
class HealthCheck(Resource):
    @health_ns.doc('health_check')
    @health_ns.marshal_with(health_response)
    @health_ns.response(200, 'Success')
    def get(self):
        """Check API health status"""
        return {
            "status": "healthy",
            "message": "Civic Issue Detection API is running",
            "timestamp": int(time.time())
        }, 200

@health_ns.route('/gemini')
class GeminiTest(Resource):
    @health_ns.doc('test_gemini')
    @health_ns.marshal_with(gemini_test_response)
    @health_ns.response(200, 'Success')
    @health_ns.response(500, 'Gemini API Error', error_response)
    def get(self):
        """Test Gemini API connection"""
        try:
            # Test with a simple text prompt
            response = model.generate_content("Respond with 'Hello from Gemini!' if you are working correctly.")
            return {
                "status": "success",
                "message": "Gemini API is working",
                "response": response.text,
                "timestamp": int(time.time())
            }, 200
        except Exception as e:
            logger.error(f"Gemini API test failed: {e}")
            api.abort(500, f"Gemini API error: {str(e)}")

# Detection Endpoints
upload_parser = reqparse.RequestParser()
upload_parser.add_argument('image', 
                          location='files',
                          type=FileStorage, 
                          required=True,
                          help='Image file for civic issue detection. Supported formats: PNG, JPG, JPEG, GIF, BMP, WEBP')

@detection_ns.route('/analyze')
class CivicIssueDetection(Resource):
    @detection_ns.doc('analyze_civic_issue')
    @detection_ns.expect(upload_parser)
    @detection_ns.marshal_with(detection_response)
    @detection_ns.response(200, 'Success')
    @detection_ns.response(400, 'Bad Request', error_response)
    @detection_ns.response(500, 'Internal Server Error', error_response)
    def post(self):
        """Analyze uploaded image for civic infrastructure issues"""
        
        # Log request details
        logger.info(f"Received POST request to /api/v1/detection/analyze")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request files: {list(request.files.keys())}")
        logger.info(f"Content type: {request.content_type}")
        
        try:
            args = upload_parser.parse_args()
            file = args['image']
            
            logger.info(f"Received file: {file.filename}, Content type: {file.content_type}")
            
            # Check if file is selected
            if file.filename == '':
                api.abort(400, "No file selected", message="Please select an image file")
            
            # Check if file is allowed
            if not allowed_file(file.filename):
                api.abort(400, "Invalid file type", 
                         message=f"Allowed file types: {', '.join(ALLOWED_EXTENSIONS)}")
            
            # Read image data
            image_data = file.read()
            logger.info(f"Image data size: {len(image_data)} bytes")
            
            # Validate image size
            if len(image_data) == 0:
                api.abort(400, "Empty file", message="The uploaded file is empty")
            
            # Validate image content
            try:
                test_image = Image.open(io.BytesIO(image_data))
                logger.info(f"Image format: {test_image.format}, Size: {test_image.size}, Mode: {test_image.mode}")
            except Exception as e:
                logger.error(f"Invalid image file: {e}")
                api.abort(400, "Invalid image file", message="The uploaded file is not a valid image")
            
            # Process image with Gemini
            logger.info("Processing image with Gemini...")
            result = process_image_with_gemini(image_data)
            logger.info(f"Gemini analysis result: {result}")
            
            # Format response for Flutter app
            if result.get('issues_found', False):
                response_data = {
                    "success": True,
                    "issues_detected": True,
                    "issues": result.get('issues', []),
                    "count": len(result.get('issues', [])),
                    "timestamp": int(time.time()),
                    "message": f"Found {len(result.get('issues', []))} civic issue(s)"
                }
            else:
                response_data = {
                    "success": True,
                    "issues_detected": False,
                    "message": result.get('message', 'No civic issues detected in the image'),
                    "issues": [],
                    "count": 0,
                    "timestamp": int(time.time())
                }
            
            logger.info(f"Sending response: {response_data}")
            return response_data, 200
            
        except Exception as e:
            logger.error(f"Error in analyze_civic_issue: {str(e)}", exc_info=True)
            api.abort(500, "Internal server error", 
                     message="An error occurred while processing the image",
                     debug_info=str(e) if app.debug else None)

# Categories Endpoints
@categories_ns.route('')
class Categories(Resource):
    @categories_ns.doc('get_categories')
    @categories_ns.marshal_with(categories_response)
    @categories_ns.response(200, 'Success')
    def get(self):
        """Get available civic issue categories"""
        categories = [
            {"id": "pothole", "name": "Pothole", "description": "Road surface damage and potholes"},
            {"id": "garbage", "name": "Garbage/Waste", "description": "Waste management issues"},
            {"id": "sewage", "name": "Sewage", "description": "Sewage overflow and drainage problems"},
            {"id": "streetlight", "name": "Street Light", "description": "Street lighting issues"},
            {"id": "infrastructure", "name": "Infrastructure", "description": "General infrastructure damage"},
            {"id": "drainage", "name": "Drainage", "description": "Blocked drains and waterlogging"},
            {"id": "sidewalk", "name": "Sidewalk", "description": "Damaged sidewalks and footpaths"},
            {"id": "traffic_signal", "name": "Traffic Signal", "description": "Traffic signal problems"},
            {"id": "illegal_dumping", "name": "Illegal Dumping", "description": "Unauthorized waste disposal"},
            {"id": "waterlogging", "name": "Waterlogging", "description": "Water accumulation issues"}
        ]
        
        return {
            "success": True,
            "categories": categories,
            "count": len(categories)
        }, 200

# Legacy endpoints for backward compatibility
@app.route('/health', methods=['GET'])
def legacy_health_check():
    """Legacy health check endpoint for backward compatibility"""
    return {
        "status": "healthy",
        "message": "Civic Issue Detection API is running",
        "timestamp": int(time.time())
    }, 200

@app.route('/report_civic_issue', methods=['POST'])
def legacy_report_civic_issue():
    """Legacy endpoint for backward compatibility"""
    # Redirect to new API endpoint logic
    # This maintains the same functionality as the original endpoint
    
    logger.info(f"Received POST request to legacy /report_civic_issue")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request files: {list(request.files.keys())}")
    logger.info(f"Content type: {request.content_type}")
    
    try:
        # Check if request has file
        if 'image' not in request.files:
            logger.error("No image file provided in request")
            return {
                "success": False,
                "error": "No image file provided",
                "message": "Please upload an image file"
            }, 400
        
        file = request.files['image']
        logger.info(f"Received file: {file.filename}, Content type: {file.content_type}")
        
        # Check if file is selected
        if file.filename == '':
            logger.error("No file selected")
            return {
                "success": False,
                "error": "No file selected",
                "message": "Please select an image file"
            }, 400
        
        # Check if file is allowed
        if not allowed_file(file.filename):
            logger.error(f"Invalid file type: {file.filename}")
            return {
                "success": False,
                "error": "Invalid file type",
                "message": f"Allowed file types: {', '.join(ALLOWED_EXTENSIONS)}"
            }, 400
        
        # Read image data
        image_data = file.read()
        logger.info(f"Image data size: {len(image_data)} bytes")
        
        # Validate image size
        if len(image_data) == 0:
            logger.error("Empty file received")
            return {
                "success": False,
                "error": "Empty file",
                "message": "The uploaded file is empty"
            }, 400
        
        # Validate image content
        try:
            test_image = Image.open(io.BytesIO(image_data))
            logger.info(f"Image format: {test_image.format}, Size: {test_image.size}, Mode: {test_image.mode}")
        except Exception as e:
            logger.error(f"Invalid image file: {e}")
            return {
                "success": False,
                "error": "Invalid image file",
                "message": "The uploaded file is not a valid image"
            }, 400
        
        # Process image with Gemini
        logger.info("Processing image with Gemini...")
        result = process_image_with_gemini(image_data)
        logger.info(f"Gemini analysis result: {result}")
        
        # Format response for Flutter app
        if result.get('issues_found', False):
            response_data = {
                "success": True,
                "issues_detected": True,
                "issues": result.get('issues', []),
                "count": len(result.get('issues', [])),
                "timestamp": int(time.time()),
                "message": f"Found {len(result.get('issues', []))} civic issue(s)"
            }
        else:
            response_data = {
                "success": True,
                "issues_detected": False,
                "message": result.get('message', 'No civic issues detected in the image'),
                "issues": [],
                "count": 0,
                "timestamp": int(time.time())
            }
        
        logger.info(f"Sending response: {response_data}")
        return response_data, 200
        
    except Exception as e:
        logger.error(f"Error in legacy report_civic_issue: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": "Internal server error",
            "message": "An error occurred while processing the image",
            "debug_info": str(e) if app.debug else None
        }, 500

@app.route('/test_gemini', methods=['GET'])
def legacy_test_gemini():
    """Legacy Gemini test endpoint for backward compatibility"""
    try:
        # Test with a simple text prompt
        response = model.generate_content("Respond with 'Hello from Gemini!' if you are working correctly.")
        return {
            "status": "success",
            "message": "Gemini API is working",
            "response": response.text,
            "timestamp": int(time.time())
        }, 200
    except Exception as e:
        logger.error(f"Gemini API test failed: {e}")
        return {
            "status": "error",
            "message": f"Gemini API error: {str(e)}"
        }, 500

@app.route('/categories', methods=['GET'])
def legacy_get_categories():
    """Legacy categories endpoint for backward compatibility"""
    categories = [
        {"id": "pothole", "name": "Pothole", "description": "Road surface damage and potholes"},
        {"id": "garbage", "name": "Garbage/Waste", "description": "Waste management issues"},
        {"id": "sewage", "name": "Sewage", "description": "Sewage overflow and drainage problems"},
        {"id": "streetlight", "name": "Street Light", "description": "Street lighting issues"},
        {"id": "infrastructure", "name": "Infrastructure", "description": "General infrastructure damage"},
        {"id": "drainage", "name": "Drainage", "description": "Blocked drains and waterlogging"},
        {"id": "sidewalk", "name": "Sidewalk", "description": "Damaged sidewalks and footpaths"},
        {"id": "traffic_signal", "name": "Traffic Signal", "description": "Traffic signal problems"},
        {"id": "illegal_dumping", "name": "Illegal Dumping", "description": "Unauthorized waste disposal"},
        {"id": "waterlogging", "name": "Waterlogging", "description": "Water accumulation issues"}
    ]
    
    return {
        "success": True,
        "categories": categories,
        "count": len(categories)
    }, 200

# Error handlers
@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return {
        "success": False,
        "error": "File too large",
        "message": "Maximum file size is 16MB"
    }, 413

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {e}")
    return {
        "success": False,
        "error": "Internal server error",
        "message": "Something went wrong on our end"
    }, 500

@app.errorhandler(404)
def not_found(e):
    """Handle not found errors"""
    return {
        "success": False,
        "error": "Not found",
        "message": "The requested endpoint was not found"
    }, 404

# Add request logging middleware
@app.before_request
def log_request_info():
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")

@app.after_request
def log_response_info(response):
    logger.info(f"Response: {response.status_code}")
    return response

if __name__ == '__main__':
    # Check if Gemini API key is set
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY environment variable is not set!")
        print("Please set it with: export GEMINI_API_KEY=your_api_key_here")
        exit(1)
    
    print("=" * 60)
    print("🚀 Starting Civic Issue Detection API with Swagger Documentation...")
    print("=" * 60)
    print("Available endpoints:")
    print("  📖 GET /docs/ - Swagger UI Documentation")
    print("  📋 GET /docs/swagger.json - OpenAPI/Swagger JSON spec")
    print("=" * 60)
    print("NEW API Endpoints (v1):")
    print("  GET /api/v1/health - Health check")
    print("  GET /api/v1/health/gemini - Test Gemini API connection")
    print("  POST /api/v1/detection/analyze - Analyze image for civic issues")
    print("  GET /api/v1/categories - Get available issue categories")
    print("=" * 60)
    print("Legacy Endpoints (for backward compatibility):")
    print("  POST /report_civic_issue - Analyze image for civic issues")
    print("  GET /health - Health check")
    print("  GET /test_gemini - Test Gemini API connection")
    print("  GET /categories - Get available issue categories")
    print("=" * 60)
    
    # Test Gemini connection on startup
    try:
        test_response = model.generate_content("Test connection")
        print("✅ Gemini API connection successful")
    except Exception as e:
        print(f"❌ Gemini API connection failed: {e}")
        print("⚠️  The API will start but image analysis may not work")
    
    print("=" * 60)
    print("🌐 Access Swagger Documentation at: http://localhost:5001/docs/")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5001)