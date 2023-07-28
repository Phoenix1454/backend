from flask import Flask, render_template, request, jsonify, Response
import mysql.connector
import pandas as pd
import sys
import io
import time
import logging
from user_agents import parse

app = Flask(__name__)



# Replace these with your actual database credentials
db_config = {
    'host': 'localhost',
    'user': 'user',
    'password': 'student',
    'database': 'leadsdb',
}
months={1:'January',2:'Feburary',3:'March',4:'April',5:'May',6:'June',7:'July',8:'August',9:'September',10:'October',11:'November',12:'December'}
# Function to initialize the database connection
totalData=0
count=0
AiSensiData=''
def init_db():
    return mysql.connector.connect(**db_config)

# Route to add leads from a CSV file
@app.route('/api/add_leads_csv', methods=['POST'])
def add_leads_csv():
    global totalData,count;
    try:
        file = request.files['file']
        if not file or not file.filename.endswith('.csv'):
            return jsonify({'error': 'Please upload a valid CSV file.'})

        df = pd.read_csv(file)
        totalData=df.dropna().shape[0]
        #csv_content = file.stream.read().decode('utf-8')
        #fd = pd.read_csv(io.StringIO(csv_content))
        #count = fd.shape[0]
        #print("count is sf",count)
        if 'name' not in df.columns or 'phone_number' not in df.columns or 'teacher' not in df.columns:
            return jsonify({'error': 'CSV file must contain columns: name, phone_number, month, year, teacher'})
        
        query = "INSERT INTO leads (name, phone_number, month, year, teacher) VALUES (%s, %s, %s, %s, %s)"
        if 'month' not in df.columns:
            month = None            
        if 'year' not in df.columns:
            year =None              
        
            for _, row in df.iterrows():
                conn = init_db()
                cursor = conn.cursor()
                phone_no=str(row['phone_number']).replace(' ','').replace('.','') # solving the error float object has no attribute replace
                phone_no=phone_no[::-1][0:10]
                phone_no=phone_no[::-1]
                try:
                    cursor.execute(query, (row['name'], phone_no, month, year, row['teacher']))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    if totalData-count>10:
                        count=count+1

                except:
                    pass
                
        else:

            for _, row in df.iterrows():
                conn = init_db()
                cursor = conn.cursor()
                year = int(row['year'])
                phone_no=str(row['phone_number']).replace(' ','').replace('.','')
                phone_no=phone_no[::-1][0:10]
                phone_no=phone_no[::-1]
                try:
                    cursor.execute(query, (row['name'], phone_no, row['month'], year, row['teacher']))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    if totalData-count>10:
                        count=count+1

                except:
                    pass
        count=totalData
        time.sleep(1)
        return jsonify({'message': 'Leads added successfully from CSV.', 'count': count})
    except Exception as e:
        return jsonify({'error': str(e)})

 
@app.route('/api/getloading', methods=['GET'])
def getLoading():
    return jsonify({'Count':count,'TotalCount':totalData})

@app.route('/api/resetloading',methods=['GET'])
def resetloading():
    global count, totalData
    count=0
    totalData=0
    return jsonify({'none':None})
# Route to add a new lead
# Route to add a new lead
@app.route('/api/add_lead', methods=['POST'])
def add_lead():
    print('added lead!', file=sys.stderr)
    data = request.json
    name = data['name']
    phone_number = data['phone_number']
    month_year = data['month_year']
    teacher_name = data['teacher']
    my = month_year.split('-')
    year = my[0]
    month = my[1]
    month = months[int(month)]

    try:
        conn = init_db()
        cursor = conn.cursor()

        # Check if a lead with the same phone number, month, and teacher already exists
        query_check_duplicate = "SELECT id FROM leads WHERE phone_number = %s AND month = %s AND year = %s AND teacher = %s"
        cursor.execute(query_check_duplicate, (phone_number, month, year, teacher_name))
        existing_lead = cursor.fetchone()

        if existing_lead:
            # If a lead with the same attributes exists, ignore the new lead
            cursor.close()
            conn.close()
            return jsonify({'message': 'Lead already exists with the same phone number, month, and teacher.'})

        # Insert the new lead since it doesn't exist with the same attributes
        query_insert = "INSERT INTO leads (name, phone_number, month, year, teacher) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query_insert, (name, phone_number, month, year, teacher_name))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Lead added successfully!'})

    except Exception as e:
        return jsonify({'error': str(e)})

# Route to get all leads
@app.route('/api/get_leads', methods=['GET'])
def get_leads():
    try:
        conn = init_db()
        cursor = conn.cursor()
        query = "SELECT * FROM leads"
        cursor.execute(query)
        leads = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'leads': leads})
    except Exception as e:
        return jsonify({'error': str(e)})
    
@app.route('/api/filter_and_download_leads', methods=['GET'])
def filter_and_download_leads():
    global AiSensiData
    try:
        month = request.args.get('month')
        year = request.args.get('year')
        teacher = request.args.get('teacher')
        month = months[int(month)]
        limit = request.args.get('limit')
        print('Filter Parameters:', month, year, teacher, limit)  # Add this line to check the values

        conn = init_db()
        cursor = conn.cursor()

        if not (teacher and month and year):
            return jsonify({"error": "Please pass all values"})

        # Build the SQL query with the filtering condition and LIMIT clause
        if limit != "0":
            query = f"SELECT * FROM leads WHERE month = %s AND year = %s AND teacher = %s LIMIT {limit}"
        else:
            query = "SELECT * FROM leads WHERE month = %s AND year = %s AND teacher = %s"
        cursor.execute(query, (month, year, teacher))

        leads = cursor.fetchall()

        # Insert the filtered leads into the usedLeads table
        query_insert = "INSERT INTO usedLeads (name, phone_number, month, year, teacher) VALUES (%s, %s, %s, %s, %s)"
        for lead in leads:
            cursor.execute(query_insert, lead[1:])
            conn.commit()

        # Create a CSV string from the leads data
        csv_data = "Name,Phone Number,Month,Year,Teacher\n"
        AiSensiData=["Name,Phone Number,Tags"]
        for lead in leads:
            csv_data += f"{lead[1]},{lead[2]},{lead[3]},{lead[4]},{lead[5]}\n"
            AiSensiData.append(f"{lead[1]},{lead[2]}")
        # Set the appropriate headers for the CSV file download
        print("Ai Sensi Data and csvData",AiSensiData,csv_data)
        response = Response(csv_data, content_type='text/csv')
        response.headers['Content-Disposition'] = 'attachment; filename=filtered_leads.csv'
        

        # Delete only the leads that are being downloaded from the leads table
        if limit != "0":
            delete_query = f"DELETE FROM leads WHERE month = %s AND year = %s AND teacher = %s LIMIT {limit}"
        else:
            delete_query = "DELETE FROM leads WHERE month = %s AND year = %s AND teacher = %s"
        cursor.execute(delete_query, (month, year, teacher))
        conn.commit()

        cursor.close()
        conn.close()

        return response

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/get_AiSensiFormat',methods=['GET'])
def get_AiSensi():
    global AiSensiData
    # fetch the tags from the req.params
    tags = request.args.get('tags')
    i=0
    correct_format="Name,Phone Number,Tags\n"
    while(i<len(AiSensiData)):
        if i:
            correct_format+=f"{AiSensiData[i]},{tags}\n"
        i+=1;
    print('Correct Data',correct_format)
    response = Response(correct_format, content_type='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=Ai_Sensi_leads.csv'
    return response
    
@app.route('/api/get_teachers', methods=['GET'])
def get_teachers():
    try:
        conn = init_db()
        cursor = conn.cursor()
        query = "SELECT DISTINCT teacher FROM leads"
        cursor.execute(query)
        teachers = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        print(teachers)
        return jsonify({'teachers': teachers})
    except Exception as e:
        return jsonify({'error': str(e)})
    
@app.route('/api/get_teacher_counts', methods=['GET'])
def get_teacher_counts():
    try:
        conn = init_db()
        cursor = conn.cursor()

        # Get leads count for each teacher from the leads table
        query_leads = "SELECT teacher, COUNT(*) FROM leads GROUP BY teacher"
        cursor.execute(query_leads)
        leads_counts = dict(cursor.fetchall())

        # Get used leads count for each teacher from the usedLeads table
        query_used_leads = "SELECT teacher, COUNT(*) FROM usedLeads GROUP BY teacher"
        cursor.execute(query_used_leads)
        used_leads_counts = dict(cursor.fetchall())

        cursor.close()
        conn.close()

        # Combine the leads count and used leads count for each teacher
        teacher_counts = {}
        for teacher in set(list(leads_counts.keys()) + list(used_leads_counts.keys())):
            teacher_counts[teacher] = {'leads': leads_counts.get(teacher, 0), 'used_leads': used_leads_counts.get(teacher, 0)}

        return jsonify(teacher_counts)
    except Exception as e:
        return jsonify({'error': str(e)})


""" @app.route('/api/loadingpercentage',methods=['GET'])
def fetch_Percentage():
    try:
        pass
    
    except:
        pass
    return jsonify({'message':'fdsf'})
 """

# Configure the logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Custom logging middleware to log IP addresses and detailed user-agent information
@app.before_request
def log_request_info():
    ip_address = request.remote_addr
    user_agent_string = request.headers.get('User-Agent')
    user_agent = parse(user_agent_string)

    browser = user_agent.browser.family
    browser_version = user_agent.browser.version_string
    os = user_agent.os.family
    os_version = user_agent.os.version_string
    device = user_agent.device.family

    logging.info(f"Request from IP: {ip_address} | Browser: {browser} {browser_version} | OS: {os} {os_version} | Device: {device} | Endpoint: {request.endpoint}")


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.jinja_env.cache = {}
    app.run(debug=True, host='0.0.0.0')
