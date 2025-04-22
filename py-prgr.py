import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from fpdf import FPDF
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# ================== 配置区 ==================
CONFIG = {
    "prom_url": "http://172.17.0.28:9090",
    "grafana_url": "http://172.17.0.28:3000",
    "dashboard_id": 1860,
    "grafana_token": "eyJrIjoidTY1ZEYwNzEzaGVET1pJbFY2Z2pNVnNmRXhxRVdLWDIiLCJuIjoicHlncmFmYW5hIiwiaWQiOjF9",
    "chrome_driver_path": "/usr/local/bin/chromedriver",
    "smtp": {
        "server": "smtp.qq.com",
        "port": 587,
        "user": "admin",
        "password": "admin",
        "receiver": ["recipient@example.com"]
    }
}


# ================== Prometheus 数据获取 ==================
def get_prom_data(query, time_range):
    start, end = time_range
    start_iso = datetime.datetime.strptime(start, "%Y-%m-%d").isoformat() + "Z"
    end_iso = datetime.datetime.strptime(end, "%Y-%m-%d").isoformat() + "Z"
    params = {"query": query, "start": start_iso, "end": end_iso, "step": "3600"}
    response = requests.get(f"{CONFIG['prom_url']}/api/v1/query_range", params=params)
    return response.json()["data"]["result"] if response.json()["status"] == "success" else []


# ================== Grafana 截图 ==================
def take_grafana_screenshot(dashboard_id, time_range):
    start, end = time_range
    url = f"{CONFIG['grafana_url']}/d/{dashboard_id}/node-exporter-full?from={start}T00:00:00Z&to={end}T23:59:59Z"
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,2000")
    driver = webdriver.Chrome(executable_path=CONFIG["chrome_driver_path"], options=chrome_options)
    driver.get(url)
    driver.implicitly_wait(10)
    screenshot_path = f"report_{start}_{end}.png"
    driver.save_screenshot(screenshot_path)
    driver.quit()
    return screenshot_path


# ================== 生成 PDF ==================
def generate_pdf(screenshot_path, prom_data, time_range):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16, style='B')
    pdf.cell(0, 10, txt="服务器性能周报", ln=1, align="C")
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt=f"时间：{time_range[0]} - {time_range[1]}", ln=1, align="C")
    pdf.image(screenshot_path, x=10, y=30, w=190)

    # 添加 Prometheus 数据
    pdf.add_page()
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(0, 10, txt="核心指标统计", ln=1, align="C")
    for item in prom_data:
        instance = item["metric"]["instance"].split(":")[0]
        value = round(float(item["values"][-1][1]) * 100, 2)
        pdf.cell(0, 8, txt=f"• {instance} CPU 使用率：{value}%", ln=1)

    pdf.output("server_report.pdf")


# ================== 主流程 ==================
if __name__ == "__main__":
    # 计算上周时间范围
    today = datetime.datetime.now()
    last_monday = today - datetime.timedelta(days=today.weekday(), weeks=1)
    last_sunday = last_monday + datetime.timedelta(days=6)
    time_range = (last_monday.strftime("%Y-%m-%d"), last_sunday.strftime("%Y-%m-%d"))

    # 1. 获取 Prometheus 数据
    cpu_query = "1 - (node_cpu_seconds_total{mode='idle'} / node_cpu_seconds_total)"
    prom_data = get_prom_data(cpu_query, time_range)

    # 2. 获取 Grafana 截图
    screenshot_path = take_grafana_screenshot(CONFIG["dashboard_id"], time_range)

    # 3. 生成 PDF
    generate_pdf(screenshot_path, prom_data, time_range)
