from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)

# SECURITY WARNING: DO NOT HARDCODE API KEYS IN PRODUCTION CODE.
# Use environment variables for security.
# Example: OPENROUTER_API_KEY_AI1 = os.environ.get("OPENROUTER_API_KEY_AI1")
# For this example, we will use placeholders.
OPENROUTER_API_KEY_AI1 = "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"
OPENROUTER_API_KEY_AI2 = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-chat-v3.1:free"

@app.route('/generate_chunk', methods=['GET'])
def generate_chunk():
    """
    Generates a 32x32 chunk for a world using a two-step AI chain.
    - AI1 generates a creative concept (biome, assets).
    - AI2 refines the idea for practicality and logical consistency.
    """
    chunk_x = int(request.args.get('chunk_x', 0))
    chunk_y = int(request.args.get('chunk_y', 0))
    
    # AI1: Creative prompt
    ai1_prompt = f"""
    You are AI1, a creative world-builder. For a 32x32 chunk at ({chunk_x},{chunk_y}), suggest a biome (e.g., forest, river) and place assets: grass, water, trees, rocks, humans, dogs. Decide if humans need dogs (e.g., farmers yes, wanderers no). Output JSON like:
    {{
        "idea": "description of chunk/biome",
        "assets": [
            {{
                "type": "tree|rock|water|grass|human|dog",
                "position": [x,y],
                "details": "e.g., has_dog for humans"
            }}
        ]
    }}
    Ensure positions are integers within 0-31 for x and y.
    """
    headers = {
        "Content-Type": "application/json",
        "HTTP-Referer": "",  # Optional, but recommended for OpenRouter
        "X-Title": ""        # Optional, but recommended for OpenRouter
    }
    
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": ai1_prompt}],
        "temperature": 1.2
    }
    
    try:
        # Call DeepSeek for AI1
        headers["Authorization"] = f"Bearer {OPENROUTER_API_KEY_AI1}"
        response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(body))
        response.raise_for_status()
        ai1_content = response.json()["choices"][0]["message"]["content"]
        
        # Robustly remove markdown code block from the response
        if ai1_content.startswith("```json"):
            ai1_content = ai1_content.strip("`").lstrip("json").strip()
        
        # AI2: Refiner prompt
        ai2_prompt = f"""
        You are AI2, a practical refiner. Refine this idea: {ai1_content}
        Ensure humans fit the biome and dogs are added logically (e.g., farmers get dogs, wanderers don’t). Keep positions as integers within 0-31. Output final JSON like:
        {{
            "idea": "refined description",
            "assets": [
                {{
                    "type": "tree|rock|water|grass|human|dog",
                    "position": [x,y],
                    "details": "e.g., has_dog for humans"
                }}
            ]
        }}
        """
        
        # Call DeepSeek for AI2
        headers["Authorization"] = f"Bearer {OPENROUTER_API_KEY_AI2}"
        body["messages"] = [{"role": "user", "content": ai2_prompt}]
        response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(body))
        response.raise_for_status()
        ai2_content = response.json()["choices"][0]["message"]["content"]
        
        # Robustly remove markdown code block from the response
        if ai2_content.startswith("```json"):
            ai2_content = ai2_content.strip("`").lstrip("json").strip()
        
        # Parse and return final JSON
        chunk_data = json.loads(ai2_content)
        return jsonify(chunk_data)
    
    except requests.RequestException as e:
        return jsonify({"error": f"API request failed: {str(e)}"}), 500
    except json.JSONDecodeError as e:
        # This will catch errors if the AI response is not valid JSON
        return jsonify({"error": f"JSON parse failed: {str(e)}", "ai_response": ai2_content}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
