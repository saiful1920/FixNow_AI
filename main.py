# main.py
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import json
import re

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize FastAPI app
app = FastAPI(
    title="FixMe AI Repair Assistant",
    description="AI-powered image analysis for repair and maintenance issues",
    version="4.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Updated System prompt with confidence score requirement
SYSTEM_PROMPT = """
You are a professional repair and maintenance diagnostic assistant. 
Analyze the provided information (images and/or text description) to identify what needs to be fixed.

Consider:
1. If images are provided, analyze them as different angles or aspects of the same problem
2. If text description is provided, use it for context about the issue
3. Provide ONE comprehensive analysis that covers all provided information
4. Assess your own confidence level in the diagnosis

Respond STRICTLY in the following JSON format:
{
    "detected_issue": "Brief title of the main issue",
    "severity": "Low/Medium/High Severity",
    "description": "Detailed explanation of the issue, including likely causes and immediate recommendations",
    "estimated_price": {
        "low": 0,
        "high": 0
    },
    "confidence": 85
}

Guidelines:
1. Analyze the information provided (images and/or description)
2. If multiple issues are present, prioritize the most critical/severe one
3. Be specific and accurate about the issues
4. Assess overall severity based on potential damage, safety risks, and urgency
5. Provide realistic price estimates in USD that cover fixing ALL identified issues
6. If images are unclear, use the description for better context
7. Price should be comprehensive for all repairs needed
8. Provide a confidence score (0-100) representing how confident you are in this diagnosis
   - Consider image clarity, description detail, and your certainty
   - 90-100: Very high confidence (clear visual evidence and detailed description)
   - 70-89: High confidence (good evidence but some ambiguity)
   - 50-69: Medium confidence (reasonable evidence but could be multiple possibilities)
   - 30-49: Low confidence (limited or unclear information)
   - 0-29: Very low confidence (insufficient or contradictory information)
"""

def analyze_with_openai(
    images_data: List[Dict[str, Any]],
    user_id: str,
    user_description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze using OpenAI's API with images and/or text description.
    Returns analysis with confidence score.
    """
    # Generate unique ID for this request
    request_id = str(uuid.uuid4())[:8]
    
    try:
        # Prepare the text prompt with clear instruction about confidence
        text_prompt = f"Analyze this repair issue and provide a confidence score (0-100). User ID: {user_id}"
        
        if user_description and user_description.strip():
            text_prompt += f"\n\nUser Description:\n{user_description}"
        
        # Add information about what was provided
        if images_data:
            text_prompt += f"\n\nNumber of images provided: {len(images_data)}"
        else:
            text_prompt += "\n\nNo images provided - analysis based on text description only."
        
        if not user_description or not user_description.strip():
            text_prompt += "\n\nNo text description provided - analysis based on images only."
        
        # Prepare content array for OpenAI
        content_items = [{"type": "text", "text": text_prompt}]
        
        # Add each image to the content (if any images provided)
        if images_data:
            for img_data in images_data:
                base64_image = base64.b64encode(img_data['content']).decode('utf-8')
                content_items.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{img_data['mime_type']};base64,{base64_image}"
                    }
                })
        
        # Determine which model to use
        if images_data:
            # Use vision model if images are provided
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": content_items
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )
        else:
            # Use regular GPT for text-only analysis
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": text_prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )
        
        # Parse response
        result_text = response.choices[0].message.content
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            analysis_result = json.loads(json_match.group())
        else:
            # Fallback: try to parse entire response as JSON
            try:
                analysis_result = json.loads(result_text)
            except:
                # Create a structured error response
                analysis_result = {
                    "detected_issue": "Analysis Error",
                    "severity": "Medium Severity",
                    "description": "Unable to parse AI response. Please try again with clearer information.",
                    "estimated_price": {"low": 0, "high": 0},
                    "confidence": 0
                }
        
        # Validate confidence score
        confidence = analysis_result.get("confidence", 0)
        
        # Ensure confidence is a number between 0 and 100
        if isinstance(confidence, str):
            # Try to extract number from string
            numbers = re.findall(r'\d+', confidence)
            if numbers:
                confidence = int(numbers[0])
            else:
                confidence = 50  # Default if can't parse
        elif not isinstance(confidence, (int, float)):
            confidence = 50
        
        # Clamp confidence between 0 and 100
        confidence = max(0, min(100, int(confidence)))
        
        # Build the final response
        result_with_metadata = {
            "user_id": user_id,
            "detected_issue": analysis_result.get("detected_issue", "Unknown Issue"),
            "severity": analysis_result.get("severity", "Medium Severity"),
            "description": analysis_result.get("description", "No description provided"),
            "estimated_price": analysis_result.get("estimated_price", {"low": 0, "high": 0}),
            "accuracy": confidence,  # This is the confidence score
            "success": True,
            "request_id": request_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "images_analyzed": len(images_data),
            "has_user_description": user_description is not None and len(user_description.strip()) > 0
        }
        
        return result_with_metadata
        
    except Exception as e:
        # Handle OpenAI API errors
        error_msg = str(e)
        
        if "rate_limit" in error_msg.lower():
            error_response = {
                "user_id": user_id,
                "detected_issue": "Service Error",
                "severity": "Low Severity",
                "description": "Rate limit exceeded. Please try again later.",
                "estimated_price": {"low": 0, "high": 0},
                "accuracy": 0,
                "request_id": str(uuid.uuid4())[:8],
                "success": False,
                "error_message": "Rate limit exceeded"
            }
        elif "invalid_api_key" in error_msg.lower():
            error_response = {
                "user_id": user_id,
                "detected_issue": "Service Error",
                "severity": "Low Severity",
                "description": "Server configuration issue. Please contact support.",
                "estimated_price": {"low": 0, "high": 0},
                "accuracy": 0,
                "request_id": str(uuid.uuid4())[:8],
                "success": False,
                "error_message": "Authentication error"
            }
        else:
            error_response = {
                "user_id": user_id,
                "detected_issue": "Analysis Failed",
                "severity": "Low Severity",
                "description": f"AI analysis failed: {error_msg}",
                "estimated_price": {"low": 0, "high": 0},
                "accuracy": 0,
                "request_id": str(uuid.uuid4())[:8],
                "success": False,
                "error_message": error_msg
            }
        
        return error_response

async def process_files(files: List[UploadFile]) -> Dict[str, Any]:
    """
    Process uploaded files.
    """
    processed_files = []
    errors = []
    
    for file in files:
        try:
            # Read file content
            contents = await file.read()
            
            # Check if file is empty
            if len(contents) == 0:
                errors.append({
                    "filename": file.filename,
                    "error": "File is empty"
                })
                continue
            
            # Check file size (max 20MB)
            max_size = 20 * 1024 * 1024
            if len(contents) > max_size:
                errors.append({
                    "filename": file.filename,
                    "error": f"File too large ({len(contents)/1024/1024:.2f}MB)"
                })
                continue
            
            # Determine MIME type
            file_extension = os.path.splitext(file.filename.lower())[1] if file.filename else ''
            mime_type = determine_mime_type(file.content_type, file_extension)
            
            processed_files.append({
                "filename": file.filename,
                "content": contents,
                "mime_type": mime_type,
                "size_bytes": len(contents)
            })
            
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": f"Processing error: {str(e)}"
            })
    
    return {
        "processed_files": processed_files,
        "errors": errors
    }

def determine_mime_type(content_type: str, file_extension: str) -> str:
    """
    Determine the MIME type of the file.
    """
    if content_type and content_type.startswith('image/'):
        return content_type
    
    # Map extension to MIME type
    extension_mapping = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff',
        '.svg': 'image/svg+xml'
    }
    
    return extension_mapping.get(file_extension, 'image/jpeg')

def validate_description(description: Optional[str]) -> bool:
    """
    Validate description length.
    """
    if description is None:
        return True
    return len(description) <= 2000

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to FixMe AI Repair Assistant",
        "status": "active",
        "version": "4.0.0",
        "endpoints": {
            "analyze": "POST /analyze - Send user_id, optional description, and optional image files",
            "health": "GET /health",
            "docs": "GET /docs (Swagger UI)"
        },
        "input_options": [
            "Only images (up to 10)",
            "Only text description",
            "Both images and text"
        ],
        "accuracy_scale": {
            "90-100": "Very high confidence (clear visual evidence and detailed description)",
            "70-89": "High confidence (good evidence but some ambiguity)",
            "50-69": "Medium confidence (reasonable evidence but could be multiple possibilities)",
            "30-49": "Low confidence (limited or unclear information)",
            "0-29": "Very low confidence (insufficient or contradictory information)"
        },
        "limits": {
            "max_images": 10,
            "max_file_size": "20MB",
            "description_max_length": "2000 characters"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "fixme-ai",
        "openai_status": "configured" if os.getenv('OPENAI_API_KEY') else "not_configured"
    }

@app.post("/analyze")
async def analyze_issues(
    user_id: str = Form(..., description="Unique identifier for the user"),
    description: Optional[str] = Form(None, description="Optional text description of the issue"),
    files: Optional[List[UploadFile]] = File(None, description="Optional list of image files")
):
    """
    Analyze repair issues using images and/or text description
    
    Args:
        user_id: Unique identifier for the user (required)
        description: Optional text description of the issue
        files: Optional list of image files (up to 10 images)
    
    Returns:
        JSON response with analysis results including accuracy score (0-100)
    """
    # Validate user_id
    if not user_id or not user_id.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Validation error",
                "message": "user_id is required and cannot be empty",
                "field": "user_id",
                "success": False
            }
        )
    
    # Validate description length if provided
    if not validate_description(description):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Validation error",
                "message": "Description too long. Maximum 2000 characters allowed.",
                "field": "description",
                "success": False
            }
        )
    
    # Check that at least one input is provided
    has_images = files is not None and len(files) > 0
    has_description = description is not None and len(description.strip()) > 0
    
    if not has_images and not has_description:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Validation error",
                "message": "At least one input is required: either images or description",
                "success": False
            }
        )
    
    # Process images if provided
    images_data = []
    if has_images:
        # Check number of images
        if len(files) > 10:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Validation error",
                    "message": "Too many images. Maximum 10 images allowed.",
                    "success": False
                }
            )
        
        # Process files
        processing_result = await process_files(files)
        
        if processing_result["errors"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "File processing error",
                    "message": f"Failed to process {len(processing_result['errors'])} file(s)",
                    "errors": processing_result["errors"],
                    "success": False
                }
            )
        
        # Prepare image data for analysis
        for processed_file in processing_result["processed_files"]:
            images_data.append({
                "content": processed_file["content"],
                "mime_type": processed_file["mime_type"]
            })
    
    # Call the AI analysis function
    analysis_result = analyze_with_openai(
        images_data=images_data,
        user_id=user_id,
        user_description=description if has_description else None
    )
    
    # Add input info to response
    analysis_result["images_analyzed_count"] = len(images_data)
    
    # Return response
    if analysis_result.get("success", False):
        return JSONResponse(
            content=analysis_result,
            status_code=200
        )
    else:
        return JSONResponse(
            content=analysis_result,
            status_code=500
        )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail if isinstance(exc.detail, dict) else {
            "error": "HTTP Exception",
            "message": str(exc.detail),
            "status_code": exc.status_code,
            "success": False
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8003,
        log_level="info"
    )