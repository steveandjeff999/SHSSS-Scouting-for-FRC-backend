from flask import Flask, render_template, request, jsonify, session, g
import pandas as pd
import os
import threading
from werkzeug.utils import secure_filename
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'your_secret_key'  # Replace with a secure key

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Function to delete the uploaded file
def delete_uploaded_file():
    file_path = session.get('file_path')
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
        session.pop('file_path', None)

@app.before_request
def before_request():
    g.session_ended = False

@app.after_request
def after_request(response):
    if g.session_ended:
        delete_uploaded_file()
    return response

@app.route('/end_session', methods=['POST'])
def end_session():
    g.session_ended = True
    session.clear()
    return jsonify({'success': 'Session ended and file deleted successfully'})

# Function to load and process the data, calculate averages
def calculate_averages(file_path, team_number=None):
    try:
        # Read the Excel file and immediately close it
        with pd.ExcelFile(file_path, engine='openpyxl') as xls:
            df = pd.read_excel(xls, sheet_name='Match Data')

        # Define the relevant columns: team number is in column 'Team Number'
        team_column = 'Team Number'

        # Columns to exclude
        exclude_columns = ['Time', 'Name', 'Match', 'Drive Team Location', 'Robot Start', 'no show', 
                           'Auto move', 'Auto Dislodged Algae', 'Dislodged Algae', 'Crossed Field', 'tipped', 'died', 
                           'end position', 'Defended', 'yellow/red card', 'commints']

        # Columns to include
        include_columns = ['Auto time', 'Auto coral L1', 'Auto coral L2', 'Auto Coral L3', 'Auto Coral L4', 
                           'Auto Barge Algae', 'Auto Processor Algae', 'Auto Foul', 'Pickup Location', 'Coral L1', 
                           'Coral L2', 'Coral L3', 'Coral L4', 'Barge Algae', 'processor Algae', 'touched opposing cage', 
                           'Offense', 'Defensive']

        # Automatically select columns to average (include only the specified columns)
        data_columns = [col for col in df.columns if col in include_columns]

        # Initialize an empty dictionary to store the averages for each team
        team_averages = {}

        # If a team number is provided, filter by that team number
        if team_number:
            # Filter the dataframe by the team number
            team_data = df[df[team_column] == int(team_number)]

            if team_data.empty:
                return {'error': f"No results found for Team {team_number}."}

            # Calculate the averages for the filtered team data, ignoring NaN values
            averages = team_data[data_columns].mean(skipna=True)
            team_averages[int(team_number)] = averages.to_dict()

        else:
            # Iterate through all unique team numbers and calculate averages
            for team in df[team_column].unique():
                # Filter the rows that match the current team number
                team_data = df[df[team_column] == team]

                # Calculate the average for each of the specified columns, ignoring NaN values
                averages = team_data[data_columns].mean(skipna=True)

                # Store the averages for the current team
                team_averages[int(team)] = averages.to_dict()

        # Save the results to a new Excel file and immediately close it
        output_file_path = os.path.join(os.path.dirname(file_path), 'team_averages.xlsx')
        with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
            averages_df = pd.DataFrame(team_averages).T  # Transpose to get teams as rows
            averages_df.to_excel(writer, index_label='Team Number')

        return {'success': "Averages calculated and saved successfully.", 'averages': team_averages}

    except Exception as e:
        return {'error': f"An error occurred: {e}"}

# Function to display match-by-match data for a selected team
def show_team_data(file_path, team_number):
    try:
        # Read the Excel file and immediately close it
        with pd.ExcelFile(file_path, engine='openpyxl') as xls:
            df = pd.read_excel(xls, sheet_name='Match Data')

        # Filter the dataframe by the team number
        team_data = df[df['Team Number'] == int(team_number)]

        if team_data.empty:
            return {'error': f"No match data found for Team {team_number}."}

        # Columns to include
        include_columns = [
            'Name', 'Match', 'Auto time', 'Auto coral L1', 'Auto coral L2', 'Auto Coral L3', 'Auto Coral L4', 
            'Auto Barge Algae', 'Auto Processor Algae', 'Auto Foul', 'Pickup Location', 'Coral L1', 
            'Coral L2', 'Coral L3', 'Coral L4', 'Barge Algae', 'processor Algae', 'touched opposing cage', 
            'Offense', 'Defensive', 'end position', 'no show', 'Auto move', 'Auto Dislodged Algae', 
            'Dislodged Algae', 'Crossed Field', 'tipped', 'died', 'Broke'
        ]

        # Filter columns based on include_columns
        team_data_filtered = team_data[include_columns]

        # Calculate scores for each match
        team_data_filtered['Score'] = team_data_filtered.apply(calculate_scores, axis=1)

        # Convert the dataframe to a dictionary
        match_data = team_data_filtered.to_dict(orient='records')

        return {'match_data': match_data}

    except Exception as e:
        return {'error': f"An error occurred: {e}"}

# Define the scoring rules
def calculate_scores(row):
    score = 0
    # Autonomous Period Scoring
    score += 3 if row['Auto move'] else 0
    score += 3 * row['Auto coral L1']
    score += 4 * row['Auto coral L2']
    score += 6 * row['Auto Coral L3']
    score += 7 * row['Auto Coral L4']
    score += 6 * row['Auto Processor Algae']
    score += 4 * row['Auto Barge Algae']
    # Tele-Operated Period Scoring
    score += 2 * row['Coral L1']
    score += 3 * row['Coral L2']
    score += 4 * row['Coral L3']
    score += 5 * row['Coral L4']
    score += 6 * row['processor Algae']
    score += 4 * row['Barge Algae']
    # Barge scoring based on end position
    if row['end position'] == 'P':
        score += 2
    elif row['end position'] == 'sc':
        score += 6
    elif row['end position'] == 'dc':
        score += 12
    return score

# Function to calculate and display team rankings
def show_team_rankings(file_path):
    try:
        # Read the Excel file and immediately close it
        with pd.ExcelFile(file_path, engine='openpyxl') as xls:
            df = pd.read_excel(xls, sheet_name='Match Data')

        # Calculate scores for each match
        df['Score'] = df.apply(calculate_scores, axis=1)

        # Calculate total scores for each team
        team_scores = df.groupby('Team Number')['Score'].sum().sort_values(ascending=False)

        # Convert the series to a dictionary
        team_rankings = team_scores.to_dict()

        return {'team_rankings': team_rankings}

    except Exception as e:
        return {'error': f"An error occurred: {e}"}

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        session['file_path'] = file_path  # Store the file path in the session
        return jsonify({'success': 'File uploaded successfully', 'file_path': file_path})

@app.route('/delete_file', methods=['POST'])
def delete_file():
    file_path = session.get('file_path')  # Retrieve the file path from the session
    if file_path and os.path.exists(file_path):
        os.remove(file_path)  # Delete the file
        session.pop('file_path', None)  # Remove the file path from the session
        return jsonify({'success': 'File deleted successfully'})
    return jsonify({'error': 'File not found'}), 404

@app.route('/get_team_averages', methods=['POST'])
def get_team_averages():
    file_path = session.get('file_path')  # Retrieve the file path from the session
    team_number = request.form.get('team_number')
    if not file_path:
        return jsonify({'error': 'File path is required.'}), 400
    result = calculate_averages(file_path, team_number)
    return jsonify(result)

@app.route('/get_all_team_averages', methods=['POST'])
def get_all_team_averages():
    file_path = session.get('file_path')  # Retrieve the file path from the session
    if not file_path:
        return jsonify({'error': 'File path is required.'}), 400
    result = calculate_averages(file_path)
    return jsonify(result)

@app.route('/get_match_data', methods=['GET'])
def get_match_data():
    file_path = session.get('file_path')  # Retrieve the file path from the session
    team_number = request.args.get('team_number')
    if not file_path:
        return jsonify({'error': 'File path is required.'}), 400
    if not team_number:
        return jsonify({'error': 'Team number is required.'}), 400
    result = show_team_data(file_path, team_number)
    return jsonify(result)

@app.route('/get_team_rankings', methods=['GET'])
def get_team_rankings():
    file_path = session.get('file_path')  # Retrieve the file path from the session
    if not file_path:
        return jsonify({'error': 'File path is required.'}), 400
    result = show_team_rankings(file_path)
    return jsonify(result)

@app.route('/get_most_died', methods=['GET'])
def get_most_died():
    file_path = session.get('file_path')  # Retrieve the file path from the session
    if not file_path:
        return jsonify({'error': 'File path is required.'}), 400
    try:
        # Read the Excel file
        with pd.ExcelFile(file_path, engine='openpyxl') as xls:
            df = pd.read_excel(xls, sheet_name='Match Data')

        # Filter the dataframe to include only the 'Team Number' and 'Broke' columns
        df_filtered = df[['Team Number', 'Broke']]
        print("Original 'Broke' column values:\n", df_filtered['Broke'].head())  # Debugging statement

        # Explicitly convert 'Broke' column to boolean based on specific values
        df_filtered['Broke'] = df_filtered['Broke'].apply(lambda x: True if str(x).lower() == 'true' else False)
        print("Converted 'Broke' column to boolean:\n", df_filtered.head())  # Debugging statement

        # Filter the dataframe to include only rows where 'Broke' is True
        df_died_true = df_filtered[df_filtered['Broke'] == True]
        print("Filtered DataFrame with 'Broke' == True:\n", df_died_true.head())  # Debugging statement

        # Count the number of 'true' values in the 'Broke' column for each team
        died_counts = df_died_true.groupby('Team Number').size().sort_values(ascending=False)
        print("Broke Counts:\n", died_counts)  # Debugging statement

        # Convert the series to a list of dictionaries
        result = [{'team': int(team), 'count': int(count)} for team, count in died_counts.items()]

        print("Result:\n", result)  # Debugging statement
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/match_points')
def match_points():
    return render_template('match_points.html')

@app.route('/calculate_match_points', methods=['POST'])
def calculate_match_points():
    file_path = session.get('file_path')
    if not file_path:
        return jsonify({'error': 'File path is required.'}), 400

    team_numbers = request.json.get('team_numbers', [])
    if len(team_numbers) != 6:
        return jsonify({'error': 'Six team numbers are required.'}), 400

    try:
        with pd.ExcelFile(file_path, engine='openpyxl') as xls:
            df = pd.read_excel(xls, sheet_name='Match Data')

        team_column = 'Team Number'
        data_columns = ['Auto time', 'Auto coral L1', 'Auto coral L2', 'Auto Coral L3', 'Auto Coral L4', 
                        'Auto Barge Algae', 'Auto Processor Algae', 'Auto Foul', 'Pickup Location', 'Coral L1', 
                        'Coral L2', 'Coral L3', 'Coral L4', 'Barge Algae', 'processor Algae', 'touched opposing cage', 
                        'Offense', 'Defensive']

        team_averages = {}
        for team_number in team_numbers:
            team_data = df[df[team_column] == int(team_number)]
            if team_data.empty:
                return jsonify({'error': f"No results found for Team {team_number}."})
            averages = team_data[data_columns].mean(skipna=True)
            team_averages[int(team_number)] = averages.to_dict()

        return jsonify({'success': 'Averages calculated successfully.', 'averages': team_averages})

    except Exception as e:
        return jsonify({'error': f"An error occurred: {e}"})

def start_flask():
    app.run(host='0.0.0.0', port=5454, debug=True, use_reloader=False)

flask_thread = threading.Thread(target=start_flask)
flask_thread.start()



