from flask import Flask, render_template, request, jsonify, Response
import mysql.connector
import pandas as pd
import sys
import io
import time


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
                phone_no=str(row['phone_number']).replace(' ','').replace('.','')
                phone_no=phone_no[::-1][0:10]
                phone_no=phone_no[::-1]
                try:
                    cursor.execute(query, (row['name'], phone_no, row['month'], row['year'], row['teacher']))
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
    count=0;
    totalData=0
    return jsonify({'none':None})
# Route to add a new lead
@app.route('/api/add_lead', methods=['POST'])
def add_lead():
    print('added lead!', file=sys.stderr)
    data = request.json
    name = data['name']
    phone_number = data['phone_number']
    month_year = data['month_year']
    teacher_name=data['teacher']
    my=month_year.split('-')
    year=my[0]
    month=my[1]
    month=months[int(month)]
    try:
        conn = init_db()
        cursor = conn.cursor()
        query = "INSERT INTO leads (name, phone_number, month, year, teacher) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (name, phone_number, month, year, teacher_name))
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
    try:
        month = request.args.get('month')
        year = request.args.get('year')
        teacher = request.args.get('teacher')
        month = months[int(month)]
        print(month)
        conn = init_db()
        cursor = conn.cursor()

        if teacher and month and year:
            query = "SELECT * FROM leads WHERE teacher = %s AND month = %s AND year = %s"
            cursor.execute(query, (teacher, month, year))
        # Add more conditions for other filter combinations if needed...

        leads = cursor.fetchall()
        cursor.close()
        conn.close()

        # Create a CSV string from the leads data
        csv_data = "Name,Phone Number,Month,Year,Teacher\n"
        for lead in leads:
            csv_data += f"{lead[1]},{lead[2]},{lead[3]},{lead[4]},{lead[5]}\n"

        # Set the appropriate headers for the CSV file download
        response = Response(csv_data, content_type='text/csv')
        response.headers['Content-Disposition'] = 'attachment; filename=filtered_leads.csv'
        return response

    except Exception as e:
        return jsonify({'error': str(e)})

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

""" @app.route('/api/loadingpercentage',methods=['GET'])
def fetch_Percentage():
    try:
        pass
    
    except:
        pass
    return jsonify({'message':'fdsf'})
 """
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.jinja_env.cache = {}
    app.run(debug=True)
