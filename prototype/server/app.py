import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import fitz  # PyMuPDF
import tempfile

# For semantic search
# You can use SentenceTransformer or any huggingface pipeline
from sentence_transformers import SentenceTransformer, util

app = Flask(__name__)
CORS(app)  # enable CORS for all routes

# Load the model once on server startup
model = SentenceTransformer('all-MiniLM-L6-v2')

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    """
    1. Receives a PDF from the React frontend.
    2. Saves it temporarily.
    3. Returns success message or an error.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    pdf_file = request.files['file']

    # Save PDF to a temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf_path = tmp.name
        pdf_file.save(pdf_path)

    return jsonify({'message': 'PDF uploaded successfully', 'pdf_path': pdf_path})

@app.route('/semantic_search', methods=['POST'])
def semantic_search():
    """
    1. Expects JSON with 'pdf_path' and 'query'.
    2. Parses PDF with PyMuPDF to extract text blocks and their coordinates.
    3. Uses the model to compute similarity scores for each text block.
    4. Returns bounding boxes with relevance scores.
    """
    data = request.get_json()
    pdf_path = data.get('pdf_path')
    query = data.get('query')

    if not pdf_path or not query:
        return jsonify({'error': 'pdf_path and query are required'}), 400

    # Encode the query
    query_embedding = model.encode(query, convert_to_tensor=True)

    results = []
    try:
        doc = fitz.open(pdf_path)
        for page_index in range(len(doc)):
            page = doc[page_index]
            blocks = page.get_text("blocks")  
            # blocks is a list of tuples: (x0, y0, x1, y1, text, block_no, ...)
            # We'll store the text + bounding box + page

            for block in blocks:
                x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
                # Compute similarity
                if text.strip():
                    block_embedding = model.encode(text.strip(), convert_to_tensor=True)
                    similarity = float(util.pytorch_cos_sim(query_embedding, block_embedding)[0][0])
                    
                    results.append({
                        'page_index': page_index,
                        'bbox': [x0, y0, x1, y1],
                        'text': text.strip(),
                        'score': similarity
                    })
        doc.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Return results sorted by score (descending)
    results_sorted = sorted(results, key=lambda r: r['score'], reverse=True)

    return jsonify({
        'results': results_sorted
    })

if __name__ == '__main__':
    # For local dev only:
    app.run(port=5000, debug=True)
