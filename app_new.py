
from http import client
from bson import ObjectId
from flask import Flask, render_template, request, redirect, session, url_for,jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets
from flask import make_response
from pymongo import MongoClient
import openai
import json
import os
from flask import send_from_directory, jsonify
from uuid import UUID
import uuid
import pandas as pd
from openai import OpenAI
from werkzeug.utils import secure_filename
import csv

app = Flask(__name__)

# Generate a secret key for Flask (you can also manually set it)
app.secret_key = "857432ad51e6839debc338502fe339b9c0d247b5895c3b1a"  # You can replace this with a manually generated key

openai_client = OpenAI(api_key="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") # Replace with your actual API key

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/mydatabase"  # Update with your DB URI
mongo = PyMongo(app)
client = MongoClient("mongodb://localhost:27017/")

# db = client["mydatabase"]
# flowcharts_collection = db["flowcharts"]
# client = MongoClient("mongodb://localhost:27017/")
db = client["mydatabase"]

SAVE_DIRECTORY = '/var/www/html/voicebot/flowcharts'
os.makedirs(SAVE_DIRECTORY, exist_ok=True)


# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        status = request.form['status']
        type = request.form['type']
        
        # Create timestamps
        created_at = datetime.utcnow()
        updated_at = created_at

        user_id = str(uuid.uuid4())  # Generate a unique user ID


        # Create user dictionary to store in MongoDB
        user = {
            "user_id": user_id,
            "name": name,
            "phone": phone,
            "email": email,
            "password": password,
            "status": status,
            "type": type,
            "created_at": created_at,
            "updated_at": updated_at
        }

        # Insert user into the MongoDB Users collection
        mongo.db.users.insert_one(user)
        print(f"User signed up: {user}")  # Print user data that was inserted
        print(f"Session data after signup (user_id): {session.get('user_id')}")
        print(f"Session data after signup (user_type): {session.get('user_type')}")

        # After successful signup, optionally store session data
        session['user_id'] = str(user['_id'])  # Store the user's ObjectId in session
        session['user_type'] = user['type']  # Store user type in session
        
        print(f"Session data updated (user_id): {session.get('user_id')}")
        print(f"Session data updated (user_type): {session.get('user_type')}")



        return redirect(url_for('login'))

    return render_template('signup.html')



@app.route('/')
def landing_page():
    return render_template('landing_page.html')  # This will be your landing page

# Route for redirecting to the landing page initially
@app.route('/redirect')
def redirect_to_landing():
    return redirect(url_for('landing_page'))  # Redirects to landing page




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')  # Get email from form
        password = request.form.get('password')  # Get password from form

        # Check if email and password are provided
        if not email or not password:
            return "Please provide both email and password.", 400
        
        # Find the user by email in the MongoDB collection
        user = mongo.db.users.find_one({"email": email})
        
        if user:
            # Debugging: print the entire user document
            print(f"User found: {user}")  # Print the entire user data to verify
            print(f"User Type: {user.get('type')}")  # Print the user's type (should be 'admin' or 'regular')

            # Check if password matches (assuming password is stored hashed)
            if check_password_hash(user['password'], password):
                print(f"User ID: {user['_id']}")
                print(f"User Type: {user.get('type')}")  # Ensure we check the 'type' field

                print(f"Session user_id: {session.get('user_id')}")
                print(f"Session user_type: {session.get('user_type')}")  # Print the user type from session

                # Set session data after successful login
                session['user_id'] = str(user['_id'])  # Store user ID in the session

                session['user_type'] = user.get('type')  # Store user type in the session
                print(f"Session user_id: {session.get('user_id')}")
                print(f"Session user_type: {session.get('user_type')}")
                

                # Login successful, redirect based on user type
                if user.get('type') == 'admin':
                    return redirect(url_for('dashboard',user_id=session['user_id']))  # Redirect to admin dashboard
                else:
                    return redirect(url_for('dashboard',user_id=session['user_id']))  # Redirect to regular user dashboard
            else:
                print("Password mismatch.")
                return "Invalid credentials, please try again.", 400  # Return error if password doesn't match

        # If user not found
        print("User not found.")
        return "Invalid credentials, please try again.", 400
    
    return render_template('login.html')


@app.route('/voicebot')
def voicebot():
    return render_template('voicebot.html')  # Serve the voicebot.html page



@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    print("user id",user_id)
    user_type = session.get('user_type')
    print(".....................",user_type)
    username = session.get('username')  # Retrieve the username from session

    
    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    # Retrieve the user data from session
    # user_type = session.get('user_type', 'regular')
    user_type = session.get('user_type') 
    print("user type",user_type)

    # user_id=session.get('user_id')
    # print("user id",user_id)
    
    # You can fetch user data from the database to render personalized info
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    name = user.get('name', 'Unknown')

    # Pass the user_type to the template
    return render_template('dashboard.html', user_type=user_type, name=name,username=username,user_id=user_id)

@app.route('/start-call/<workflow_uuid>', methods=['POST'])
def start_call(workflow_uuid):
    try:
        # Retrieve user_id from query params
        user_id = session.get('user_id')
        print(f"Received User ID: {user_id}")
        print(f"Received Workflow UUID: {workflow_uuid}")
        data = request.get_json()
        mobile_number = data.get('mobile_number')
        print("mobile number: ",mobile_number)
        
        # Query MongoDB to fetch data based on workflow_uuid and user_id
        workflow_data = db.prompt_data1.find_one({"uuid": workflow_uuid, "user_id": user_id})
        print("workflow data:",workflow_data)

        if not workflow_data:
            # If no data found, return an error message
            return jsonify({"error": "No workflow data found for the given user and workflow ID."}), 404

        # Log the fetched data for debugging
        print(f"Fetched Workflow Data: {workflow_data}")

        # Extract specific values from workflow_data
        language = workflow_data.get('language')
        voice = workflow_data.get('voice')
        call_duration = workflow_data.get('call_duration')
        interruption = workflow_data.get('interruption')
        ivr_detect = workflow_data.get('ivr_detect')

        print(f"Language: {language}, Voice: {voice}, Call Duration: {call_duration}, Interruption: {interruption}, IVR Detect: {ivr_detect}")

                 # Check if 'blocks' exist and print them as formatted JSON
        if "levels" in workflow_data:
            levels_data = workflow_data['levels']
            data=json.dumps(levels_data, indent=4)
            print("levels-------")
            print(data)

            # Fetch the CSV file path from workflow_data (assuming you store the CSV path here)
            csv_file_path = workflow_data.get('csv_files')
            if not csv_file_path or not os.path.exists(csv_file_path):
                return jsonify({"error": "CSV file not found at the provided path."}), 404
            
            print(csv_file_path)
            
             # Read and process CSV file
            csv_data = []
            with open(csv_file_path, mode='r') as file:
                csv_reader = csv.DictReader(file)  # Read as dictionaries
                for row in csv_reader:
                    csv_data.append(row)

            print("CSV Data:", csv_data)  # Log the CSV data for debugging

            # Find the data related to the provided mobile number in the CSV file
            user_csv_data = None
            for row in csv_data:
                if row.get('Mobile_Number') == mobile_number:
                    user_csv_data = row
                    break

            if not user_csv_data:
                return jsonify({"error": "Mobile number not found in CSV."}), 404
            
            print(f"Data for Mobile Number {mobile_number}: {user_csv_data}")
            # call_uuid = existing["uuid"] if existing else str(uuid.uuid4())

            #  # Define the placeholder map based on user_csv_data
            # placeholder_map = {
            #     "{customer_name}": user_csv_data.get('Customer_Name'),
            #     "{mobile_number}": user_csv_data.get('Mobile_Number'),
            #     "{credit_card_last_4}": user_csv_data.get('Credit_Card_Last_4'),
            #     "{overdue_days}": user_csv_data.get('Overdue_Days'),
            #     "{overdue_amount}": user_csv_data.get('Overdue_Amount')
            # }

             # Fetch selected_columns from workflow_data
            selected_columns = workflow_data.get('selected_columns', [])
            print("selected columns: ",selected_columns)

            # Build the placeholder map based on the selected_columns
            placeholder_map = {}
            for column in selected_columns:
                placeholder_map[f"{{{column.lower()}}}"] = user_csv_data.get(column, "")

            # Replace the placeholders in the 'blocks_data' JSON using the placeholder_map
            updated_blocks_data = replace_placeholders_in_json(levels_data, placeholder_map)


            # Replace the placeholders in the 'blocks_data' JSON using the placeholder_map
            updated_blocks_data = replace_placeholders_in_json(levels_data, placeholder_map)
            
            # Print the updated blocks data after placeholder replacement
            print("Updated Blocks Data (after placeholder replacement):")
            print(json.dumps(updated_blocks_data, indent=4))


            # Call a function to generate the response prompt (e.g., for GPT-3/AI processing)
            response = generate_dynamic_prompt_using_json(updated_blocks_data)
            print("Generated Response:", response)
            # return response

            
            # print("Blocks:")
            # print(json.dumps(blocks_data, indent=4))  # Pretty print the blocks as JSON
            # print("Blocks:")
            # print(json.dumps(workflow['blocks'], indent=4))  # Pretty print the blocks as JSON

        else:
            print("No blocks found in this workflow.")


        # You can process the data further or use it for your application's logic here
        # For example, return the data in the response
        return jsonify({"message": "Call started successfully!", "workflow_data": workflow_data, "language": language,
                "voice": voice,
                "call_duration": call_duration,
                "interruption": interruption,
                "ivr_detect": ivr_detect,
                "user_csv_data": user_csv_data}), 200

    except Exception as e:
        # Catch and log any errors
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500



def replace_placeholders_in_json(json_data, placeholder_map):
    """Recursively replace placeholders in a nested JSON."""
    if isinstance(json_data, dict):
        # If the current element is a dictionary, iterate through its keys
        for key, value in json_data.items():
            json_data[key] = replace_placeholders_in_json(value, placeholder_map)
    elif isinstance(json_data, list):
        # If the current element is a list, iterate through its elements
        for index in range(len(json_data)):
            json_data[index] = replace_placeholders_in_json(json_data[index], placeholder_map)
    elif isinstance(json_data, str):
        # If it's a string, replace the placeholders using the map
        for placeholder, replacement in placeholder_map.items():
            json_data = json_data.replace(placeholder, str(replacement))
    
    print("json data: ",json_data)
    
    return json_data


@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    print("user id",user_id)
    user_type = session.get('user_type')
    print(".....................",user_type)
    username = session.get('username')  # Retrieve the username from session

    
    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    # Retrieve the user data from session
    # user_type = session.get('user_type', 'regular')
    user_type = session.get('user_type') 
    print("user type",user_type)
    
    # You can fetch user data from the database to render personalized info
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    name = user.get('name', 'Unknown')

    # Pass the user_type to the template
    return render_template('profile.html', user_type=user_type, name=name,username=username)


@app.route('/workflow_page')
def workflow_page():
    user_id = session.get('user_id')
    print("user id",user_id)
    # username = session.get('username')  # Retrieve the username from session
    user_type = session.get('user_type') 
     # You can fetch user data from the database to render personalized info
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    name = user.get('name', 'Unknown')
    
    # if not username:
        # return redirect(url_for('login'))  # Redirect to login if username not found
    
    return render_template('workflow_page.html',name=name ,user_type=user_type,user_id=user_id)  # The page for designing a workflow




@app.route('/api/submit-csv-api', methods=['POST'])
def submit_csv_api():
    data = request.json
    api_url = data.get('api_url')
    print("api url: ",api_url)
    workflow_uuid = data.get('workflow_uuid')
    print("workflow uuid: ",workflow_uuid)
    user_id = data.get('user_id')
    print("user id: ",user_id)

    if not api_url or not workflow_uuid:
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    # collection = db.prompt_data1  # Replace with your actual collection name

    # Check if the document exists based on `workflow_uuid`
    existing_doc = db.prompt_data1.find_one({"uuid": workflow_uuid})

    if existing_doc:
        # Update existing document and append to `api_urls` list

        if "api_urls" in existing_doc and api_url in existing_doc["api_urls"]:
            return jsonify({"success": False, "message": "You have already added this API URL."})

        db.prompt_data1.update_one(
            {"uuid": workflow_uuid},
            {"$set": {"user_id": user_id}, "$push": {"api_urls": api_url}}
        )
        return jsonify({"success": True, "message": "API URL updated successfully"})
    else:
        # Insert a new document
        new_doc = {
            "uuid": workflow_uuid,
            "user_id": user_id,
            "api_urls": [api_url]
        }
        db.prompt_data1.insert_one(new_doc)
        return jsonify({"success": True, "message": "API URL added successfully"})


# @app.route('/dashboard_workflow1')
# def dashboard_workflow1():
#     bot_name = request.args.get('botName')
#     bot_uuid = request.args.get('botUuid')
#     workflow_uuid = request.args.get('workflowUuid')
#     user_id = request.args.get('userId')
#     workflow_data = request.args.get('workflow_data')
#     user_id = session.get('user_id')

#     return render_template('dashboard_workflow1.html', workflow_data=workflow_data,user_id=user_id, bot_name=bot_name, bot_uuid=bot_uuid, workflow_uuid=workflow_uuid)


@app.route('/dashboard_workflow1')
def dashboard_workflow1():
    # Retrieve query parameters
    bot_name = request.args.get('botName')
    bot_uuid = request.args.get('botUuid')
    workflow_uuid = request.args.get('workflowUuid')
    
    # Get user_id from session
    user_id = session.get('user_id')

    # Ensure required parameters are present
    if not bot_name or not bot_uuid or not workflow_uuid or not user_id:
        # Handle missing parameters (you might want to redirect to an error page or send a message)
        return "Missing required parameters", 400

    # Optional: Retrieve workflow_data if needed (ensure it's passed in the URL if required)
    workflow_data = request.args.get('workflow_data')

    # Render the template and pass all the necessary variables
    return render_template('dashboard_workflow1.html', 
                           workflow_data=workflow_data,
                           user_id=user_id, 
                           bot_name=bot_name, 
                           bot_uuid=bot_uuid, 
                           workflow_uuid=workflow_uuid)

# @app.route('/api/save-workflow1', methods=['POST'])
# def save_workflow1():
#     try:
#         # Get the JSON data from the frontend
#         workflow_data = request.get_json()
#         uuid = workflow_data.get('workflowUuid')  # Extract UUID from the frontend data
#         # user_id=request.get_json()
#         # user_id = workflow_data.get('userId')  # Adjust the key if needed
        
#         # Find the existing workflow in the database based on uuid
#         existing_workflow = db.prompt_data1.find_one({"uuid": uuid})

#         # print(user_id)

#         print("workflow data in json: ",workflow_data)
      
#         # user_id = session.get('user_id')
#         # workflow_data['user_id'] = user_id

#         # Insert the workflow data into MongoDB
#         result =db.prompt_data1.update_one(workflow_data)

#         # Return a success response
#         return jsonify({"status": "success", "message": "Workflow saved successfully!", "id": str(result.inserted_id)}), 200

#     except Exception as e:
#         # Return an error response if something goes wrong
#         return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/save-workflow1', methods=['POST'])
def save_workflow1():
    try:
        # Get the JSON data from the frontend
        workflow_data = request.get_json()

        # Extract the uuid from the incoming data
        uuid = workflow_data.get('workflowUuid')  # Extract UUID from the frontend data

        # Ensure the fields are consistent with the database fields (if necessary)
        if 'userId' in workflow_data:
            workflow_data['user_id'] = workflow_data.pop('userId')
        if 'voicebotUuid' in workflow_data:
            workflow_data['voicebot_uuid'] = workflow_data.pop('voicebotUuid')
        if 'workflowName' in workflow_data:
            workflow_data['workflow_name'] = workflow_data.pop('workflowName')
        if 'workflowUuid' in workflow_data:
            workflow_data['uuid'] = workflow_data.pop('workflowUuid')

        # Check if uuid is provided
        if not uuid:
            return jsonify({"status": "error", "message": "UUID is required!"}), 400

        # Find the existing workflow in the database based on uuid
        existing_workflow = db.prompt_data1.find_one({"uuid": uuid})

        if existing_workflow:
            # If the workflow with the given uuid exists, update it with the new data
            update_data = {
                "$set": workflow_data  # Update or add fields without removing existing ones
            }

            result = db.prompt_data1.update_one(
                {"uuid": uuid},  # Find the document with the given uuid
                update_data  # Update the document without removing other existing fields
            )

            if result.modified_count > 0:
                message = "Workflow updated successfully!"
                workflow_id = uuid  # Using the uuid as the workflow ID
            elif result.matched_count > 0:
                message = "Workflow already up to date."
                workflow_id = uuid
            else:
                message = "No matching workflow found."
                workflow_id = None
        else:
            # If no workflow with the given uuid exists, insert a new workflow
            result = db.prompt_data1.insert_one(workflow_data)
            message = "New workflow saved successfully!"
            workflow_id = str(result.inserted_id)

        # Return a success response
        return jsonify({"status": "success", "message": message, "id": workflow_id}), 200

    except Exception as e:
        # Return an error response if something goes wrong
        return jsonify({"status": "error", "message": str(e)}), 500


# @app.route('/api/get-workflow1/<workflow_uuid>', methods=['GET'])
# def get_workflow(workflow_uuid):
#     try:
#         print(workflow_uuid)
#         user_id = session.get('user_id')
#         # Fetch the workflow data from MongoDB
#         workflow_data = db.prompt_data1.find_one({"uuid": workflow_uuid}, {'_id': 0})
        
#         if workflow_data:
#             # Redirect to the dashboard_workflow page with the workflow data
#             return redirect(url_for('dashboard_workflow', workflow_data=json.dumps(workflow_data)))
#         else:
#             return jsonify({"status": "error", "message": "Workflow not found"}), 404

#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/get-workflow1/<workflow_uuid>', methods=['GET'])
def get_workflow1(workflow_uuid):
    try:
        user_id = session.get('user_id')  # Get user_id from session
        print("user id:",user_id)
        if not user_id:
            return jsonify({"status": "error", "message": "User not authenticated"}), 401

        print(f"Fetching workflow for User ID: {user_id}, Workflow UUID: {workflow_uuid}")

        # Fetch the workflow data from MongoDB
        workflow_data = db.prompt_data1.find_one({"uuid": workflow_uuid, "user_id": user_id}, {'_id': 0})

        if workflow_data:
            # Redirect to the dashboard_workflow page with the workflow data
            return redirect(url_for('dashboard_workflow', workflow_data=json.dumps(workflow_data)))
        else:
            return jsonify({"status": "error", "message": "Workflow not found or unauthorized access"}), 404

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/logout', methods=['POST'])
def logout():
    # Clear the session (or any other logout-related logic)
    session.pop('user_id', None)
    return redirect(url_for('login'))  # Redirect to the login page after logout


@app.route('/create_voicebot')
def create_voicebot():
    return render_template('create_voicebot.html')  # The page for creating a new voicebot

# @app.route('/prompt_page')
# def create_voicebot():
#     return render_template('prompt_page.html')  # The page for creating a new voicebot

# Route for prompt_page.html
@app.route('/prompt-page')
def prompt_page():
    user_id = session.get('user_id')
    # username = session.get('username')  # Retrieve the username from session
    user_type = session.get('user_type') 
     # You can fetch user data from the database to render personalized info
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    name = user.get('name', 'Unknown')
    print("redirect to the prompt page")
    return render_template('prompt_page.html',name=name ,user_type=user_type)  # Renders the HTML template

@app.route('/manage_voicebot')
def manage_voicebot():
    return render_template('manage_voicebot.html')  # The page for managing voicebots


@app.route('/static/js/script.js')
def script_js():
    response = make_response(open('static/js/script.js').read())
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response




def generate_prompt(dynamic_workflow):
    print("generate prompt function running")
    
    # Craft the dynamic prompt based on the input workflow
    # prompt = f"""You are an automated assistant. Take this workflow description: {dynamic_workflow} 
    # and generate a comprehensive prompt that will dynamically handle all steps in the workflow. 
    # The prompt should clearly outline the required steps and expectations for proper execution. define the workflow steps properly and work according to the workflow and before the initial greeting add the prompt like the you are an automated use name from the workflow and your work is to dynamic handle conversation add htis before the initial greeting also add instruction to handle workflow conversation dynamically"""
    prompt = f"""Your task is to generate text using this which includes the text like You are a vidya an automated voice assistant  and use name from  and add this text append to the  text  Your goal is to guide the customer through a conversation about the overdue payment based on their responses.
        
        You should maintain a polite, understanding, and empathetic tone, focusing on helping the customer understand the overdue payment issue. and below that add this workflow steps {dynamic_workflow} and in the workflow steps give informat customer response, bot resposne and detailed next step strictly follow this format for each step below that add instructions 7. **Additional Notes:**
        - Always maintain a polite and empathetic tone while addressing customers.
        - Use GPT-3 to understand the conversation context and dynamically adjust the flow.
        - Always ensure to record and keep track of all conversations for continued context during interactions.
        - Strictly follow the exact sentences and responses in the workflow. """

    # Create a conversation message with the system role
    messages = [{"role": "user", "content": prompt}]
    
    # Make the request to OpenAI API
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Specify the model
            messages=messages
        )
        # Extract the message from the response
        generated_response = response['choices'][0]['message']['content']
        # print("GPT prompt response:", generated_response)
        return generated_response

    except Exception as e:
        print(f"Error generating prompt: {str(e)}")
        return None

def generate_dynamic_prompt_using_json(data):
    
    print("generate prompt function running")
    
    # Craft the dynamic prompt based on the input workflow
    # prompt = f"""You are an automated assistant. Take this workflow description: {dynamic_workflow} 
    # and generate a comprehensive prompt that will dynamically handle all steps in the workflow. 
    # The prompt should clearly outline the required steps and expectations for proper execution. define the workflow steps properly and work according to the workflow and before the initial greeting add the prompt like the you are an automated use name from the workflow and your work is to dynamic handle conversation add htis before the initial greeting also add instruction to handle workflow conversation dynamically"""
    prompt = f"""
    
            
        You are a virtual assistant helping design a conversation workflow based on the following JSON data. Each level contains stages with a bot’s dialogue, client responses, and the next stage.

            The structure is as follows:
            Each stage has an ID, a dialogue, a repeat count, and the next stage(s).
            The conversation moves based on the client’s response.

            Please generate a step-by-step workflow showing how the conversation progresses based on the JSON data provided. 

            Here is the JSON data:

            {data}

            For example:
            
            For Level 0, Stage 0A: The bot says: "<dialogue>". Depending on the client’s response, it moves to either Stage 1A or Stage 1B (based on nextStage).
            Then, based on the next stage(s), continue the workflow, showing the bot’s dialogue and the client’s potential response leading to the next stage.

            If the nextStage is empty, indicate that the conversation ends.

            Now, apply this workflow logic to the provided data.

         
          
            """
    # Create a conversation message with the system role
    # messages = [{"role": "user", "content": prompt}]
    
    # Make the request to OpenAI API
    try:
        openai_resp = openai_client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[{"role": "user", "content": prompt}]
            )
        generated_response = openai_resp.choices[0].message.content.strip()
       
        # print("GPT prompt response:", generated_response)
        return generated_response

    except Exception as e:
        print(f"Error generating prompt: {str(e)}")
        return None
  
collection1 = db['prompt_data']  # Replace 'workflows' with your MongoDB collection name

@app.route("/get-workflows", methods=["GET"])
def get_workflows():
    try:
        # Check if 'file' is part of the request
        # user_id = request.form.get('user_id')  # Retrieve user_id from request
        print("start")
        user_id = session.get('user_id')
        bot_id = request.args.get('bot_id')
        print("Request Args:", request.args)  # Debugging
        print("user id********",user_id)
        print("bot id********",bot_id)
         # Fetch workflows from MongoDB for the given user_id
        workflows = list(mongo.db.prompt_data1.find({"user_id": user_id, "voicebot_uuid": bot_id}, {"_id": 0, "uuid": 1, "workflow_name": 1}))

        # Fetch all workflow UUIDs or names from MongoDB
        # workflows = collection1.find({}, {"uuid": 1})  # Fetch only UUID or any unique field to list workflows
        # workflow_list = [workflow["uuid"] for workflow in workflows]
        workflow_list = [{"uuid": workflow["uuid"], "workflowName": workflow.get("workflow_name")} for workflow in workflows]
        print(workflow_list)

        
        return jsonify(workflow_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/api/voicebots', methods=['GET'])
def get_voicebots():
    user_id = session.get('user_id')
    voicebots = db.voicebots_collection1.find({'user_id':user_id})  # Adjust 'voicebots' collection name if necessary
    voicebot_list = []
    for bot in voicebots:
        voicebot_list.append({
            'id': str(bot['_id']),
            'bot_id': bot['bot_id'],
            'bot_name': bot['bot_name']
        })
    print(voicebot_list)
    return jsonify(voicebot_list)

# Endpoint to delete a voicebot by bot_id
@app.route('/api/voicebots/<string:bot_id>', methods=['DELETE'])
def delete_voicebot(bot_id):
    user_id = request.json.get('user_id')  # Get user_id from the request

    # Access the 'voicebots' collection in your MongoDB
    
    
    # Find the voicebot by bot_id and user_id (if applicable)
    voicebot = db.prompt_data1.find_one({"bot_id": bot_id, "user_id": user_id})
    
    if voicebot:
        # If the bot exists, delete it
        db.prompt_data1.delete_one({"bot_id": bot_id, "user_id": user_id})
        return jsonify({"success": True, "message": "Voicebot deleted successfully."}), 200
    else:
        return jsonify({"success": False, "message": "Voicebot not found."}), 404



@app.route('/get-workflow-json/<workflow_id>', methods=['GET'])
def get_workflow_json(workflow_id):
    try:
        print("start")
        user_id = session.get('user_id')
        print("user id:",user_id)
        print("workflow id:",workflow_id)


        # workflow = db.prompt_data.find_one({
        #     "uuid": workflow_id,
        #     "user_id": user_id
        # })
      
       
        # workflow_list = [{"uuid": workflow["uuid"], "workflowName": workflow.get("workflow_name")} in workflow]

        workflow_data = db.prompt_data1.find_one({"uuid": workflow_id, "user_id": user_id}, {'_id': 0})
       
        print("workflow data :____________________________________-",workflow_data)


        return jsonify({"success": True, "data": workflow_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    


@app.route('/dashboard/<section>')
def dashboard_section(section):
    return render_template('dashboard.html', active_section=section)


prompt_data_collection = db["prompt_data"]  # Replace with your collection name

@app.route('/delete-workflow-json/<uuid>', methods=['DELETE'])
def delete_workflow(uuid):
    try:
         # Check if 'file' is part of the request
        user_id = request.args.get('user_id')  # Retrieve user_id from request
        print(f"Request URL: {request.url}")  # Debugging the full URL to see what is being sent
        print("Request Args:", request.args)  # Debugging
        print("user id---------------",user_id)
        # Delete the document from the collection based on the UUID
        result = collection1.delete_one({"uuid": uuid, "user_id": user_id})
        
        if result.deleted_count == 0:
            return jsonify({"error": "Workflow not found"}), 404
        
        return jsonify({"message": "Workflow deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/save-workflow-json/<uuid_filename>", methods=["POST"])
def save_workflow(uuid_filename):
    try:
        # Get the JSON data from the request
        flowchart_json = request.get_json()
        print(flowchart_json)
        formatted_json = json.dumps(flowchart_json, indent=4, ensure_ascii=False)
        print(formatted_json)

        blocks = []
        connections = []

        # Extract blocks and connections from the flowchart data
        for key, value in flowchart_json['drawflow'].items():
            for block_id, block_data in value['data'].items():
                # if "html" in block_data:
                #     # Ensure newlines remain intact by stripping surrounding quotes
                #     block_data["html"] = json.dumps(block_data["html"], ensure_ascii=False)[1:-1]

                block = {
                    "id": block_data["id"],
                    "name": block_data["name"],
                    "data": block_data["data"]["block"],  # Extracting the block data
                    "inputs": block_data["inputs"],  # Storing the inputs data
                    "outputs": block_data["outputs"],  # Storing the outputs data
                }
                blocks.append(block)

                # Extract connections
                for input_slot, input_data in block_data['inputs'].items():
                    for connection in input_data['connections']:
                        connections.append({
                            "input": input_slot,
                            "output": connection.get("output"),
                            "node": connection.get("node")
                        })

        # Prepare the flowchart data to insert or update in MongoDB
        flowchart_data = {
            "uuid": uuid_filename,  # Use the UUID from the URL or request
            "content": flowchart_json,  # Storing entire flowchart content
            "blocks": blocks,  # Store the extracted blocks
            # "connections": connections  # Store the extracted connections
        }

        # Save the flowchart data to MongoDB (updating or inserting)
        result = collection.update_one(
            {"uuid": uuid_filename},  # Find the document by UUID
            {"$set": flowchart_data},  # Update the document with the new data
            upsert=True  # If the document doesn't exist, create a new one
        )

        # Check if the document was modified or inserted
        if result.modified_count > 0:
            message = "Workflow updated successfully"
        else:
            message = "Workflow saved (new document inserted)"

        return jsonify({
            "message": message,
            "uuid": uuid_filename
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Helper function to validate UUID
def is_valid_uuid(uuid_string):
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False

@app.route('/save-flowchart', methods=['POST'])
def save_flowchart():
    try:
        # Get JSON data from the request
        data = request.get_json()
        print("Received Flowchart Data:", data)

        # Extract blocks data from the received JSON
        blocks = data.get("blocks", [])
        print("Extracted Blocks:", blocks)

        # Get the current flowchart ID (e.g., flowchart 1, flowchart 2)
        current_flowchart_id = mongo.db.flowcharts.count_documents({}) + 1
        print("Current Flowchart ID:", current_flowchart_id)

        # Insert the flowchart with the new ID
        flowchart_data = {
            "flowchart_id": current_flowchart_id,
            "blocks": blocks
        }

        # Insert the flowchart into MongoDB
        result = mongo.db.flowcharts.insert_one(flowchart_data)
        print("Flowchart Saved:", result)

        # Fetch the inserted flowchart by its ID
        saved_flowchart = mongo.db.flowcharts.find_one({"_id": result.inserted_id})
        print(f"Saved Flowchart Data: {saved_flowchart}")

        # Fetch the latest flowchart data from the database (excluding _id)
        flowchart_data = mongo.db.flowcharts.find_one(
            {"flowchart_id": current_flowchart_id},
            {"_id": 0}
        )

        # Fetch the flowchart data from the database using flowchart_id
        current_flowchart_id = saved_flowchart.get("flowchart_id")
        flowchart_data_from_db = mongo.db.flowcharts.find_one(
            {"flowchart_id": current_flowchart_id},
            {"_id": 0}  # Excluding the _id from the fetched data
        )

        if flowchart_data_from_db:
            # Save the fetched flowchart data to a JSON file
            file_path = os.path.join(SAVE_DIRECTORY, f"flowchart_{current_flowchart_id}.json")
            with open(file_path, 'w') as f:
                json.dump(flowchart_data_from_db, f, indent=4)

        #     return jsonify({"success": True, "message": "Flowchart saved and data fetched successfully"})
        # else:
        #     return jsonify({"success": False, "message": "Flowchart not found"}), 404
    

        # Convert the list of blocks into a dictionary for easy access
        flowchart_dict = {node["id"]: node for node in flowchart_data["blocks"]}

        # Function to create dynamic workflow text
        def generate_dynamic_workflow(flowchart_dict):
            workflow_text = ""
            previous_data_block_name = ""  # Initialize before the loop
            print("Generating dynamic workflow...")
            block_no = 1  # Start numbering from 1

            # Iterate through blocks to generate the dynamic workflow text
            for node in flowchart_dict.values():
                parent_id = node["parent"]
                # Check if the block name is different from the previous one
                if previous_data_block_name != node["data_block_name"]:
                    workflow_text += f"{block_no}. {node['data_block_name']}:"
                    previous_data_block_name = node["data_block_name"]
                    block_no += 1

                    if parent_id == -1:
                        # Root block (no parent)
                        workflow_text += f"\n- {node['input_bot_message']}\n\n"
                    else:
                        # Child block (has parent)
                        parent = flowchart_dict.get(parent_id, {})
                        parent_block = parent.get("data_block_name", "Unknown Block")
                        workflow_text += (
                            f"- \nIf the customer responds with '{node['input_customer_message']}' (or similar phrases) in '{parent_block}':\n"
                            f"  Respond with: '{node['input_bot_message']}'\n\n"
                        )
                else:
                    # If the data block name is the same as the previous one
                    if parent_id == -1:
                        workflow_text += f"\n- {node['input_bot_message']}\n\n"
                    else:
                        parent = flowchart_dict.get(parent_id, {})
                        parent_block = parent.get("data_block_name", "Unknown Block")
                        workflow_text += (
                            f"- \nIf the customer responds with '{node['input_customer_message']}'(or similar phrases) in '{parent_block}':\n"
                            f"  Respond with: '{node['input_bot_message']}'\n\n"
                        )

            print(workflow_text)
            return workflow_text

        # Generate the dynamic workflow text
        dynamic_workflow = generate_dynamic_workflow(flowchart_dict)
        print("Generated Dynamic Workflow:", dynamic_workflow)

        # Call a function to generate the response prompt (e.g., for GPT-3/AI processing)
        response = generate_prompt(dynamic_workflow)
        print("Generated Response:", response)

        # Return a success response with the generated workflow and response
        return jsonify({
            "message": f"Flowchart {current_flowchart_id} saved successfully",
            "flowchart_id": current_flowchart_id,  # Returning the flowchart_id
            "inserted_id": str(result.inserted_id),
            "dynamic_workflow": dynamic_workflow,
            "response": response,
            "success": True, 
            "redirect_url": url_for('prompt_page')
        }), 200

    except Exception as e:
        # Handle any exceptions and send an error response
        return jsonify({"error": str(e)}), 500




UPLOAD_FOLDER = "/var/www/html/voicebot/flowchart"
UPLOAD_CSV_FOLDER = "/var/www/html/voicebot/csv_files"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# collection = db["flowchart"]  # Collection name
collection = db["prompt_data"]  # Collection for flowchart blocks and connections

# @app.route("/export-flowchart", methods=["POST"])
# def export_flowchart():
#     try:
#         print("Request received")
#         user_id = session.get('user_id')

#         workflow_name = request.form.get('workflowName')
#         user_id = request.form.get('user_id')
#         language = request.form.get("language")
#         voice = request.form.get("voice")
#         call_duration = request.form.get("call_duration")
#         interruption = request.form.get("interruption")
#         ivr_detect = request.form.get("ivr_detect")
#         bot_message = request.form.get("bot_message")
#         voicebot_name = request.form.get('voicebotName')  # New field
#         voicebot_uuid = request.form.get('voicebotUuid')  # New field


#         print(f"Received workflow name: {workflow_name}")
#         print(f"User ID: {user_id}")

#         if "file" not in request.files:
#             return jsonify({"error": "No file uploaded"}), 400

#         file = request.files["file"]

#         if file.filename == "":
#             return jsonify({"error": "Empty file"}), 400

#         # Extract the UUID from the filename
#         uuid_filename = file.filename.split('.')[0]  # Assuming UUID is the base name of the file
#         print(f"Received file UUID: {uuid_filename}")

#         # Read and parse file content
#         file_content = file.read().decode('utf-8')
#         flowchart_json = json.loads(file_content)
        
#         # Format JSON for better readability
#         formatted_json = json.dumps(flowchart_json, indent=4, ensure_ascii=False)
#         print("Formatted JSON:", formatted_json)

#         # Extract blocks and connections
#         blocks = []
#         connections = []

#         for key, value in flowchart_json['drawflow'].items():
#             for block_id, block_data in value['data'].items():
#                 if "html" in block_data:
#                     block_data["html"] = json.dumps(block_data["html"], ensure_ascii=False)[1:-1]  # Ensure newlines remain intact

#                 block = {
#                     "id": block_data["id"],
#                     "name": block_data["name"],
#                     "data": block_data["data"]["block"],
#                     "inputs": block_data["inputs"],
#                     "outputs": block_data["outputs"],
#                 }
#                 blocks.append(block)
                
#                 for input_slot, input_data in block_data['inputs'].items():
#                     for connection in input_data['connections']:
#                         connections.append({
#                             "input": input_slot,
#                             "output": connection.get("output"),
#                             "node": connection.get("node")
#                         })

#         flowchart_data = {
#             "user_id":user_id,
#             "uuid": uuid_filename,
#             "workflow_name": workflow_name,
#             "user_id": user_id,
#             "voicebot_name":voicebot_name,
#             "voicebot_uuid":voicebot_uuid,
#             "language": language,
#             "voice": voice,
#             "call_duration": call_duration,
#             "interruption": interruption,
#             "ivr_detect": ivr_detect,
#             "bot_message": bot_message,
#             "content": json.loads(formatted_json),
#             "blocks": blocks
            
#         }

#         # **Check if UUID already exists in MongoDB**
#         existing_workflow = collection.find_one({"uuid": uuid_filename})

#         if existing_workflow:
#             # **Update the existing document**
#             collection.update_one(
#                 {"uuid": uuid_filename},
#                 {"$set": flowchart_data}
#             )
#             print(f"Updated existing flowchart in MongoDB with UUID: {uuid_filename}")
#             message = "Workflow updated successfully"
#         else:
#             # **Insert new workflow data**
#             collection.insert_one(flowchart_data)
#             print(f"Inserted new flowchart in MongoDB with UUID: {uuid_filename}")
#             message = "Workflow saved successfully"

#         return jsonify({
#             "message": message,
#             "uuid": uuid_filename
#         }), 200

#     except Exception as e:
#         print(f"Error: {str(e)}")
#         return jsonify({"error": str(e)}), 500


@app.route("/export-flowchart", methods=["POST"])
def export_flowchart():
    try:

        uuid = request.form.get("uuid")
        print("Request received")
        user_id = session.get('user_id')

        workflow_name = request.form.get('workflowName')
        user_id = request.form.get('user_id')
        language = request.form.get("language")
        voice = request.form.get("voice")
        call_duration = request.form.get("call_duration")
        interruption = request.form.get("interruption")
        ivr_detect = request.form.get("ivr_detect")
        bot_message = request.form.get("bot_message")
        voicebot_name = request.form.get('voicebotName')  # New field
        voicebot_uuid = request.form.get('voicebotUuid')  # New field


       


        flowchart_data = {
            "user_id":user_id,
            "uuid": uuid,  # Ensure UUID is stored properly
            "workflow_name": workflow_name,
            "user_id": user_id,
            "voicebot_name":voicebot_name,
            "voicebot_uuid":voicebot_uuid,
            "language": language,
            "voice": voice,
            "call_duration": call_duration,
            "interruption": interruption,
            "ivr_detect": ivr_detect,
            "bot_message": bot_message,
           
        }

        # **Check if UUID already exists in MongoDB**
        existing_workflow = mongo.db.prompt_data1.find_one({"uuid": uuid})

        if existing_workflow:
            # **Update the existing document**
            mongo.db.prompt_data1.update_one(
                {"uuid": uuid},
                {"$set": flowchart_data}
            )
            print(f"Updated existing flowchart in MongoDB with UUID: {uuid}")
            message = "Workflow updated successfully updated"
        else:
            # **Insert new workflow data**
            mongo.db.prompt_data1.insert_one(flowchart_data)
            print(f"Inserted new flowchart in MongoDB with UUID: {uuid}")
            message = "Workflow saved successfully inserted" 

        return jsonify({
            "message": message,
            "uuid": uuid
        }), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
voicebots_collection="voicebots"

@app.route('/create_bot', methods=['POST'])
def create_bot():
    
    data = request.get_json()
    
    bot_name = data.get('bot_name')
    bot_id = data.get('bot_id')

    user_id = session.get('user_id')
     # You can fetch user data from the database to render personalized info
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    name = user.get('name', 'Unknown')

    print("user id",user_id)
    user_type = session.get('user_type')
    print(".....................",user_type)
    username = session.get('username')  # Retrieve the username from session


    # Store bot info in MongoDB
    bot_data = {
        'bot_id': bot_id,
        'bot_name': bot_name,
        'user_id':user_id
    }
    
    # Insert bot data into MongoDB collection
    result = db.voicebots_collection1.insert_one(bot_data)

    # Check if insertion was successful
    if result.inserted_id:
        return jsonify({'success': True, 'bot_id': bot_id,"name":name,"user_id":user_id})
    else:
        return jsonify({'success': False, 'error': 'Failed to save bot'})

# @app.route("/upload_csv", methods=["POST"])
# def upload_csv():
#     user_id = session.get('user_id')

#     # Check if the file is part of the request
#     if "file" not in request.files:
#         return jsonify({"message": "No file part"}), 400

#     # Get the file from the request
#     file = request.files["file"]
    
#     # Retrieve form data
#     voicebot_uuid = request.form.get("voicebotUuid", "").strip()
#     voicebot_name = request.form.get("voicebotName", "").strip()
#     workflow_id = request.form.get("uuid", "").strip()
#     workflow_name = request.form.get("workflowName", "").strip()

#     # Log values for debugging
#     print("*****************************voicebot uuid", voicebot_uuid)
#     print("********voicebot name ", voicebot_name)
#     print("workflow id**********", workflow_id)
#     print("workflow name*********", workflow_name)

#     # Ensure file is not empty and has a valid extension
#     if file.filename == "":
#         return jsonify({"message": "No selected file"}), 400

#     if not file.filename.endswith(".csv"):
#         return jsonify({"message": "Invalid file format. Please upload a CSV file."}), 400

#     try:
#         # Read the CSV file into a DataFrame
#         df = pd.read_csv(file)
#         data = df.to_dict(orient="records")  # Convert CSV to list of dictionaries

#         # Don't add workflow-specific data to individual records in the CSV
#         # Just store the raw CSV records
#         for index, record in enumerate(data, start=1):
#             record["id"] = index  # Sequential ID (1, 2, 3, ...)
#         # Document to be inserted into MongoDB
#         print(workflow_id)
#         document = {
#             "voicebotUuid": voicebot_uuid,
#             "workflow_id": workflow_id,
#             "workflowName": workflow_name,
#             "voicebotName": voicebot_name,
#             "csvData": data  # Store all CSV records inside a list as "csvData"
#         }

#         # Insert the document into MongoDB
#         db.csv_data.insert_one(document)

#         return jsonify({"message": "CSV uploaded and stored successfully in a single document!"}), 200

#     except Exception as e:
#         print(f"Error processing CSV: {e}")
#         return jsonify({"message": f"Error processing CSV file: {str(e)}"}), 500

@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    user_id = session.get('user_id')

    # Check if the file is part of the request
    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400

    file = request.files["file"]

    # Retrieve form data
    voicebot_uuid = request.form.get("voicebotUuid", "").strip()
    voicebot_name = request.form.get("voicebotName", "").strip()
    workflow_id = request.form.get("uuid", "").strip()
    workflow_name = request.form.get("workflowName", "").strip()

    # Log values for debugging
    print("Voicebot UUID:", voicebot_uuid)
    print("Voicebot Name:", voicebot_name)
    print("Workflow ID:", workflow_id)
    print("Workflow Name:", workflow_name)

    # Ensure file is valid
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400
    if not file.filename.endswith(".csv"):
        return jsonify({"message": "Invalid file format. Please upload a CSV file."}), 400

    try:
        # Secure filename and define file path
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_CSV_FOLDER, filename)
        
        # Save the file
        file.save(file_path)
        # Check if the workflow exists and update or insert accordingly
        existing_workflow = db.prompt_data1.find_one({"uuid": workflow_id})

        if existing_workflow:
            # If workflow exists, update the file path
            result = db.prompt_data.update_one(
                {"uuid": workflow_id},  # Find document by workflow_id
                {"$set": {"csv_files": file_path}}  # Set the file path
            )
            if result.modified_count > 0:
                return jsonify({"message": "CSV file uploaded and stored successfully (updated workflow).", "file_path": file_path}), 200
            else:
                return jsonify({"message": "No changes made to the workflow (file path already exists)."}), 200
        else:
            # If workflow does not exist, create a new document
            new_workflow = {
                "uuid": workflow_id,
                "user_id": user_id,
                "voicebot_uuid": voicebot_uuid,
                "voicebot_name": voicebot_name,
                "workflow_name": workflow_name,
                "csv_files": file_path,
                "selected_columns": []  # Initialize empty or default selected_columns
            }
            db.prompt_data1.insert_one(new_workflow)
            return jsonify({"message": "CSV file uploaded and stored successfully (new workflow created).", "file_path": file_path}), 201


        # # Update the existing document in `prompt_data` by appending the file path
        # result = db.prompt_data.update_one(
        #     {"uuid": workflow_id},  # Find document by workflow_id
        #     {"$set": {"csv_files": file_path}}  # Append file path to `csv_files` array
        # )

        # if result.matched_count == 0:
        #     return jsonify({"message": "Workflow ID not found!"}), 404

        # return jsonify({"message": "CSV file uploaded and stored successfully!", "file_path": file_path}), 200

    except Exception as e:
        print(f"Error processing CSV: {e}")
        return jsonify({"message": f"Error processing CSV file: {str(e)}"}), 500


    
# @app.route('/get_columns_for_workflow/<workflow_id>', methods=['GET'])
# def get_columns_for_workflow(workflow_id):
#     print("start")
#     # Fetch document for the given workflow_id
#     document = db.csv_data.find_one({"workflow_id": workflow_id})
    
#     if document and "csvData" in document and len(document["csvData"]) > 0:
#         # Extract column names from the first entry of the csvData
#         columns = list(document["csvData"][0].keys())
        
        
#         # Remove 'id' if you don't want it as a column (or leave it if necessary)
#         if 'id' in columns:
#             columns.remove('id')
        
#         print(columns)
        
#         return jsonify({"columns": columns})
#     else:
#         return jsonify({"message": "No columns found for this workflow."}), 404

# @app.route('/get_columns_for_workflow/<workflow_id>', methods=['GET'])
# def get_columns_for_workflow(workflow_id):
#     print("start")

#     # Fetch document for the given workflow_id from prompt_data
#     document = db.prompt_data.find_one({"uuid": workflow_id})

#     if document and "csvData" in document and len(document["csvData"]) > 0:
#         # Extract column names from the first entry of csvData
#         columns = list(document["csvData"][0].keys())

#         # Remove 'id' if you don't want it as a column
#         if 'id' in columns:
#             columns.remove('id')

#         print(columns)
#         return jsonify({"columns": columns})

#     else:
#         return jsonify({"message": "No columns found for this workflow."}), 404

@app.route('/get_columns_for_workflow/<workflow_id>', methods=['GET'])
def get_columns_for_workflow(workflow_id):
    print("Start fetching columns")

    # Fetch document for the given workflow_id from prompt_data
    document = db.prompt_data1.find_one({"uuid": workflow_id})

    if not document:
        return jsonify({"message": "Workflow not found."}), 404

    # Get the CSV file path from the document
    csv_file_path = document.get("csv_files")

    if not csv_file_path:
        return jsonify({"message": "CSV file not found for this workflow."}), 404

    try:
        # Read the CSV file and extract columns
        df = pd.read_csv(csv_file_path)
        columns = list(df.columns)

        # Remove 'id' column if present
        if 'id' in columns:
            columns.remove('id')

        print("Extracted columns:", columns)
        return jsonify({"columns": columns})

    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return jsonify({"message": f"Error reading CSV file: {str(e)}"}), 500


  
# @app.route('/save_variable_mapping', methods=['POST'])
# def save_variable_mapping():
#     try:
#         # Get the data from the request body
#         data = request.get_json()
#         workflow_id = data.get('workflowId')
#         selected_columns = data.get('selectedColumns')
#         print(selected_columns)
#         print(workflow_id)

#         if not workflow_id or not selected_columns:
#             return jsonify({'error': 'Workflow ID or selected columns are missing'}), 400

#         # Update or create the workflow with the selected columns (variable mappings)
#         # If 'selected_columns' exists, append new values. If not, update them directly.
#         db.prompt_data.update_one(
#             {"uuid": workflow_id},
#             {
#                 # "$set": {"selected_columns": selected_columns}  # This will overwrite the entire array
#                 "$addToSet": {"selected_columns": {"$each": new_columns}}  # Appends new columns without duplicates

#             },
#             upsert=True  # If no document is found, create a new one
#         )

#         return jsonify({'success': True, 'message': 'Variable mapping saved successfully'})

#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@app.route('/save_variable_mapping', methods=['POST'])
def save_variable_mapping():
    try:
        # Get the data from the request body
        data = request.get_json()
        workflow_id = data.get('workflowId')
        selected_columns = data.get('selectedColumns')
        print(f"Selected Columns: {selected_columns}")
        print(f"Workflow ID: {workflow_id}")

        if not workflow_id or not selected_columns:
            return jsonify({'error': 'Workflow ID or selected columns are missing'}), 400

        # Find the existing workflow data in the database
        existing_workflow = db.prompt_data1.find_one({"uuid": workflow_id})

        if existing_workflow:
            # Get the existing selected_columns for this workflow
            existing_columns = existing_workflow.get('selected_columns', [])

            # Append only new columns that aren't already present
            new_columns = [col for col in selected_columns if col not in existing_columns]

            if new_columns:
                # If there are new columns to add, update the document
                db.prompt_data1.update_one(
                    {"uuid": workflow_id},
                    {
                        "$addToSet": {"selected_columns": {"$each": new_columns}}  # Appends new columns without duplicates
                    }
                )
                return jsonify({'success': True, 'message': 'Variable mapping updated successfully'})
            else:
                return jsonify({'success': True, 'message': 'No new columns to add. Mapping is already up to date.'})
        else:
            # If workflow does not exist, create a new one with the provided columns
            new_workflow = {
                "uuid": workflow_id,
                "selected_columns": selected_columns  # Directly set the new selected columns
            }
            db.prompt_data1.insert_one(new_workflow)
            return jsonify({'success': True, 'message': 'New workflow created with variable mapping.'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500




if __name__ == '__main__':
    app.run(debug=True,port=5001,host="0.0.0.0")



