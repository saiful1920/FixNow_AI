# FixMe AI Repair Assistant API

A professional AI-powered image analysis API for diagnosing repair and maintenance issues using OpenAI's GPT-4o vision model.

## Overview

FixMe AI analyzes images and text descriptions to identify repair issues, assess severity, estimate costs, and provide confidence scores for diagnoses. The API accepts either images, text descriptions, or both for comprehensive analysis.

## Features

- 🔍 **Multi-Modal Analysis**: Accepts images, text, or both
- 🎯 **Confidence Scoring**: Returns accuracy scores (0-100) for each diagnosis
- 💰 **Cost Estimation**: Provides price ranges in USD
- ⚠️ **Severity Assessment**: Categorizes issues as Low, Medium, or High severity
- 📸 **Multiple Images**: Supports up to 10 images per request
- 🚀 **Fast Processing**: Powered by OpenAI GPT-4o

## Base URL

```
http://localhost:8003
```

## Authentication

Currently, no authentication required. API key for OpenAI is configured server-side via environment variables.

## Endpoints

### 1. Root Endpoint

**GET** `/`

Returns API information and available endpoints.

**Response:**
```json
{
  "message": "Welcome to FixMe AI Repair Assistant",
  "status": "active",
  "version": "4.0.0",
  "endpoints": { ... },
  "accuracy_scale": { ... },
  "limits": { ... }
}
```

### 2. Health Check

**GET** `/health`

Check API service status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-05T10:30:00",
  "service": "fixme-ai",
  "openai_status": "configured"
}
```

### 3. Analyze Issues (Main Endpoint)

**POST** `/analyze`

Analyze repair issues using images and/or text description.

**Content-Type:** `multipart/form-data`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Unique identifier for the user |
| `description` | string | No | Text description of the issue (max 2000 chars) |
| `files` | file[] | No | Image files (max 10, 20MB each) |

**Note:** At least one of `description` or `files` must be provided.

**Supported Image Formats:**
- JPEG (.jpg, .jpeg)
- PNG (.png)
- WebP (.webp)
- GIF (.gif)
- BMP (.bmp)
- TIFF (.tiff, .tif)
- SVG (.svg)

**Response Structure:**

```json
{
  "user_id": "user123",
  "detected_issue": "Leaking Kitchen Faucet",
  "severity": "Medium Severity",
  "description": "The faucet appears to have a worn-out O-ring or washer causing water to drip continuously...",
  "estimated_price": {
    "low": 50,
    "high": 150
  },
  "accuracy": 85,
  "success": true,
  "request_id": "a1b2c3d4",
  "analysis_timestamp": "2026-01-05T10:30:00",
  "images_analyzed": 2,
  "has_user_description": true,
  "images_analyzed_count": 2
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string | The user identifier provided in request |
| `detected_issue` | string | Brief title of the identified issue |
| `severity` | string | Issue severity: "Low Severity", "Medium Severity", or "High Severity" |
| `description` | string | Detailed analysis including causes and recommendations |
| `estimated_price.low` | number | Lower bound of repair cost estimate (USD) |
| `estimated_price.high` | number | Upper bound of repair cost estimate (USD) |
| `accuracy` | number | Confidence score (0-100) in the diagnosis |
| `success` | boolean | Whether analysis was successful |
| `request_id` | string | Unique identifier for this analysis |
| `analysis_timestamp` | string | ISO timestamp of analysis |
| `images_analyzed` | number | Number of images processed |
| `has_user_description` | boolean | Whether text description was provided |

## Confidence Score Scale

| Range | Confidence Level | Description |
|-------|-----------------|-------------|
| 90-100 | Very High | Clear visual evidence and detailed description |
| 70-89 | High | Good evidence but some ambiguity |
| 50-69 | Medium | Reasonable evidence, multiple possibilities |
| 30-49 | Low | Limited or unclear information |
| 0-29 | Very Low | Insufficient or contradictory information |

## Usage Examples

### Example 1: Image-Only Analysis

```bash
curl -X POST http://localhost:8003/analyze \
  -F "user_id=user123" \
  -F "files=@broken_pipe.jpg" \
  -F "files=@pipe_closeup.jpg"
```

### Example 2: Text-Only Analysis

```bash
curl -X POST http://localhost:8003/analyze \
  -F "user_id=user123" \
  -F "description=My kitchen sink is leaking from the base of the faucet"
```

### Example 3: Combined Analysis (Images + Text)

```bash
curl -X POST http://localhost:8003/analyze \
  -F "user_id=user123" \
  -F "description=Water damage on ceiling, appears to be from upstairs bathroom" \
  -F "files=@ceiling_damage.jpg" \
  -F "files=@water_stain.jpg"
```

### Example 4: Python Client

```python
import requests

url = "http://localhost:8003/analyze"

# Prepare data
data = {
    "user_id": "user123",
    "description": "Crack in the wall near window"
}

files = [
    ("files", open("wall_crack1.jpg", "rb")),
    ("files", open("wall_crack2.jpg", "rb"))
]

# Send request
response = requests.post(url, data=data, files=files)

# Parse response
result = response.json()
print(f"Issue: {result['detected_issue']}")
print(f"Severity: {result['severity']}")
print(f"Confidence: {result['accuracy']}%")
print(f"Cost Estimate: ${result['estimated_price']['low']} - ${result['estimated_price']['high']}")
```

### Example 5: JavaScript (Fetch API)

```javascript
const formData = new FormData();
formData.append('user_id', 'user123');
formData.append('description', 'Electrical outlet not working');
formData.append('files', imageFile1);
formData.append('files', imageFile2);

fetch('http://localhost:8003/analyze', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => {
  console.log('Issue:', data.detected_issue);
  console.log('Severity:', data.severity);
  console.log('Confidence:', data.accuracy + '%');
  console.log('Price:', `$${data.estimated_price.low} - $${data.estimated_price.high}`);
})
.catch(error => console.error('Error:', error));
```

## Error Responses

### 400 Bad Request - Missing Required Field

```json
{
  "error": "Validation error",
  "message": "user_id is required and cannot be empty",
  "field": "user_id",
  "success": false
}
```

### 400 Bad Request - No Input Provided

```json
{
  "error": "Validation error",
  "message": "At least one input is required: either images or description",
  "success": false
}
```

### 400 Bad Request - Too Many Images

```json
{
  "error": "Validation error",
  "message": "Too many images. Maximum 10 images allowed.",
  "success": false
}
```

### 400 Bad Request - Description Too Long

```json
{
  "error": "Validation error",
  "message": "Description too long. Maximum 2000 characters allowed.",
  "field": "description",
  "success": false
}
```

### 500 Internal Server Error - Analysis Failed

```json
{
  "user_id": "user123",
  "detected_issue": "Analysis Failed",
  "severity": "Low Severity",
  "description": "AI analysis failed: [error details]",
  "estimated_price": {
    "low": 0,
    "high": 0
  },
  "accuracy": 0,
  "request_id": "e5f6g7h8",
  "success": false,
  "error_message": "Detailed error message"
}
```

## Limits and Constraints

| Limit | Value |
|-------|-------|
| Maximum images per request | 10 |
| Maximum file size per image | 20 MB |
| Maximum description length | 2000 characters |
| Supported image formats | JPEG, PNG, WebP, GIF, BMP, TIFF, SVG |

## Setup and Installation

### Prerequisites

- Python 3.8+
- OpenAI API key
- pip package manager

### Installation Steps

1. **Clone or download the project**

2. **Install dependencies**
```bash
pip install fastapi uvicorn openai python-multipart python-dotenv
```

3. **Create `.env` file**
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

4. **Run the server**
```bash
python main.py
```

The API will be available at `http://localhost:8003`

### Alternative: Using uvicorn directly

```bash
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

## API Documentation (Swagger UI)

Interactive API documentation is available at:

```
http://localhost:8003/docs
```

This provides a web interface to test all endpoints directly from your browser.

## Best Practices

1. **Provide Context**: Include both images and text descriptions for best results and higher confidence scores
2. **Multiple Angles**: Submit multiple images from different angles of the same issue
3. **Clear Images**: Use well-lit, focused images for better analysis
4. **Detailed Descriptions**: Provide relevant details like when the issue started, symptoms, location
5. **User IDs**: Use consistent user_id values for tracking and analytics
6. **Error Handling**: Always check the `success` field in responses and handle errors appropriately

## Troubleshooting

### Issue: "openai_status": "not_configured"

**Solution:** Set the `OPENAI_API_KEY` environment variable in your `.env` file

### Issue: Rate limit exceeded

**Solution:** The OpenAI API has rate limits. Wait a few moments and try again, or upgrade your OpenAI plan

### Issue: File too large error

**Solution:** Compress images to under 20MB or use lower resolution images

### Issue: Low confidence scores

**Solution:** Provide clearer images, add text descriptions, or submit multiple angles of the issue

## Support

For issues or questions:
- Check the `/health` endpoint for service status
- Review error messages in the response
- Ensure your OpenAI API key is valid and has sufficient credits

## Version History

- **v4.0.0** - Added confidence scoring, support for text-only analysis, improved error handling
- **v3.x** - Multi-image support
- **v2.x** - Initial vision API integration
- **v1.x** - Basic repair analysis

---

**Note:** This API uses OpenAI's GPT-4o model which requires an active OpenAI API key with available credits. Ensure your API key is properly configured before use.
