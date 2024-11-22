import os
from flask import Flask, request, render_template
from dotenv import load_dotenv

# Import Azure Cognitive Search libraries
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# Initialize Flask application
app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()
search_endpoint = os.getenv('SEARCH_SERVICE_ENDPOINT')
search_key = os.getenv('SEARCH_SERVICE_QUERY_KEY')
search_index = os.getenv('SEARCH_INDEX_NAME')

# Ensure all required environment variables are loaded
if not all([search_endpoint, search_key, search_index]):
    raise ValueError("Missing required environment variables in .env file.")

# Function to query Azure Cognitive Search
def search_query(search_text, filter_by=None, sort_order=None):
    """
    Wrapper function to query Azure Cognitive Search.
    :param search_text: The search string provided by the user.
    :param filter_by: Filter expression for the query.
    :param sort_order: Sorting order for the query results.
    :return: Search results object.
    """
    try:
        # Create Azure Search client
        azure_credential = AzureKeyCredential(search_key)
        search_client = SearchClient(search_endpoint, search_index, azure_credential)

        # Submit the search query
        results = search_client.search(
            search_text,
            search_mode="all",  # Use "all" to match across all fields
            include_total_count=True,
            filter=filter_by,
            order_by=sort_order,
            facets=['metadata_author'],  # Example facet for filtering
            highlight_fields='merged_content-3,imageCaption-3',  # Highlight specific fields
            select=(
                "metadata_storage_name,metadata_author,metadata_storage_size,"
                "metadata_storage_last_modified,language,merged_content,"
                "keyphrases,locations,imageTags,imageCaption, sentiment"
            )  # Updated select clause with valid fields
        )
        return results

    except Exception as ex:
        # Log error and re-raise it for error handling
        print(f"Error querying Azure Search: {ex}")
        raise

# Home page route
@app.route("/")
def home():
    """
    Renders the home page.
    """
    return render_template("default.html")

# Search results route
@app.route("/search", methods=['GET'])
def search():
    """
    Handles search queries and renders the results page.
    """
    try:
        # Get the search term from the request parameters
        search_text = request.args.get("search", "").strip()
        if not search_text:
            return render_template("error.html", error_message="Search term cannot be empty.")

        # Process optional facet and sorting parameters
        filter_expression = None
        if 'facet' in request.args:
            filter_expression = f"metadata_author eq '{request.args['facet']}'"

        # Determine sorting order
        sort_expression = 'search.score()'  # Default sort by relevance
        sort_field = request.args.get("sort", "relevance")
        if sort_field == 'file_name':
            sort_expression = 'metadata_storage_name asc'
        elif sort_field == 'size':
            sort_expression = 'metadata_storage_size desc'
        elif sort_field == 'date':
            sort_expression = 'metadata_storage_last_modified desc'
        elif sort_field == 'sentiment':
            sort_expression = 'sentiment desc'

        # Query Azure Search and retrieve results
        results = search_query(search_text, filter_expression, sort_expression)

        # Render the results page
        return render_template("search.html", search_results=results, search_terms=search_text)

    except Exception as error:
        # Handle errors and render error page
        print(f"Error during search: {error}")
        return render_template("error.html", error_message=str(error))

# Ensure the Flask app runs only when executed directly
if __name__ == "__main__":
    # Enable debugging for development
    app.run(debug=True, port=5051)
