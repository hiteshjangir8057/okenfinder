# app.py
from flask import Flask, render_template, request, send_file
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import pandas as pd
import time
import sys
import subprocess
import io
from xhtml2pdf import pisa
from flask import make_response
from jinja2 import Template

app = Flask(__name__)
data_cache = []

@app.route('/', methods=['GET', 'POST'])
def index():
    global data_cache
    if request.method == 'POST':
        field = request.form['field']
        query = request.form['query']
        data_cache = fetch_data(field, query)
    return render_template('index.html', data=data_cache)

@app.route('/download')
def download_excel():
    global data_cache
    if not data_cache:
        return "No data to export.", 400
    df = pd.DataFrame(data_cache, columns=["Form Ref No", "Student Name", "Father's Name"])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    return send_file(output, download_name="student_data.xlsx", as_attachment=True)

@app.route('/download-pdf')
def download_pdf():
    global data_cache
    if not data_cache:
        return "No data to export.", 400
    html = render_template("pdf_template.html", data=data_cache)
    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result)
    if pisa_status.err:
        return "Error generating PDF", 500
    result.seek(0)
    return send_file(result, download_name="student_data.pdf", as_attachment=True)

def fetch_data(field, value):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    creation_flags = 0
    if sys.platform.startswith('win'):
        creation_flags = subprocess.CREATE_NO_WINDOW

    service = Service()
    service.creationflags = creation_flags
    driver = webdriver.Chrome(service=service, options=options)

    driver.get("https://exam.shekhauniexam.in/search_ref_number.aspx")
    time.sleep(2)

    field_map = {
        "Student Name": "1",
        "Father's Name": "2",
        "Date of Birth": "3",
        "Mobile Number": "4"
    }

    fields_to_check = {
        "1": "Student Name",
        "2": "Father's Name",
        "3": "Date of Birth",
        "4": "Mobile Number"
    }

    choice = field_map[field]

    for key, field_name in fields_to_check.items():
        if key != choice:
            driver.execute_script(f"""
                const divs = document.querySelectorAll('.col-md-6.mb-3');
                for (let div of divs) {{
                    if (div.innerText.includes("{field_name}")) {{
                        div.remove();
                    }}
                }}
            """)

    if choice == "1":
        driver.find_element(By.ID, "ContentPlaceHolder1_txtname").send_keys(value)
    elif choice == "2":
        driver.find_element(By.ID, "ContentPlaceHolder1_txtfname").send_keys(value)
    elif choice == "3":
        dob_field = driver.find_element(By.ID, "ContentPlaceHolder1_txtdob")
        dob_field.click()
        time.sleep(0.5)
        dob_field.send_keys(value)
    elif choice == "4":
        driver.find_element(By.ID, "ContentPlaceHolder1_txtmob").send_keys(value)

    driver.find_element(By.ID, "ContentPlaceHolder1_btnstatus").click()
    time.sleep(3)

    table = driver.find_element(By.ID, "ContentPlaceHolder1_grddata")
    rows = table.find_elements(By.TAG_NAME, "tr")
    data = []
    for row in rows[1:]:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 3:
            data.append([cols[0].text, cols[1].text, cols[2].text])

    driver.quit()
    return data

if __name__ == '__main__':
    app.run(debug=True)