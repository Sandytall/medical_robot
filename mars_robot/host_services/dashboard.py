#!/usr/bin/env python3
"""
Mars Robot Doctor Dashboard
FastAPI web interface for monitoring patient health data and robot status
"""
import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Data models
class HealthLog(BaseModel):
    id: Optional[int] = None
    patient_id: str
    symptoms: str
    voice_log: str
    sentiment: str
    severity_level: int
    doctor_notified: bool = False
    timestamp: datetime

class PatientInfo(BaseModel):
    id: str
    name: str
    age: Optional[int] = None
    illness: Optional[str] = None
    medications: Optional[str] = None
    photo_count: int = 0
    registered_at: datetime
    last_seen: Optional[datetime] = None

class RobotStatus(BaseModel):
    current_mode: str
    cpu_usage: float
    memory_usage: float
    temperature: float
    hardware_ready: bool
    emergency_stopped: bool
    timestamp: datetime

class ErrorReport(BaseModel):
    component: str
    error_type: str
    message: str
    traceback: Optional[str] = None
    timestamp: datetime

# Initialize FastAPI app
app = FastAPI(
    title="Mars Robot Doctor Dashboard",
    description="Real-time monitoring and management interface for Mars hospital robot",
    version="1.0.0"
)

# Database configuration
DATABASE_PATH = os.environ.get('DATABASE_PATH', '/shared_data/database/patients.db')
DB_DIR = os.path.dirname(DATABASE_PATH)

# Ensure database directory exists
Path(DB_DIR).mkdir(parents=True, exist_ok=True)

# Global variables
error_reports: List[ErrorReport] = []
latest_robot_status: Optional[RobotStatus] = None

def init_database():
    """Initialize database tables if they don't exist"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            # Create patients table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    age INTEGER,
                    illness TEXT,
                    medications TEXT,
                    face_encodings BLOB,
                    photo_count INTEGER DEFAULT 0,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP
                )
            ''')

            # Create health_logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS health_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT,
                    symptoms TEXT,
                    voice_log TEXT,
                    sentiment TEXT,
                    severity_level INTEGER,
                    doctor_notified BOOLEAN DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients (id)
                )
            ''')

            conn.commit()
            print("✅ Database initialized successfully")

    except Exception as e:
        print(f"❌ Database initialization error: {e}")

def get_db_connection():
    """Get database connection with optimizations for concurrent access"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
    # Enable WAL mode for better concurrent access (robot + dashboard)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print("🌐 Starting Mars Robot Doctor Dashboard...")
    init_database()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker"""
    return {"status": "healthy", "timestamp": datetime.now()}

# Main dashboard page
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mars Robot - Doctor Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .panel { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .status-indicator { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
            .status-online { background: #27ae60; }
            .status-warning { background: #f39c12; }
            .status-offline { background: #e74c3c; }
            .health-log { border-left: 4px solid #3498db; padding: 10px; margin: 10px 0; background: #ecf0f1; }
            .severity-low { border-left-color: #27ae60; }
            .severity-medium { border-left-color: #f39c12; }
            .severity-high { border-left-color: #e74c3c; }
            .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }
            .btn-primary { background: #3498db; color: white; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #34495e; color: white; }
            .timestamp { font-size: 0.9em; color: #7f8c8d; }
            .error-report { background: #fff5f5; border: 1px solid #e74c3c; border-radius: 4px; padding: 10px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 Mars Robot - Doctor Dashboard</h1>
            <p>Real-time monitoring and patient management</p>
        </div>

        <div class="container">
            <div class="panel">
                <h2>Robot Status</h2>
                <div id="robot-status">
                    <span class="status-indicator status-offline"></span>
                    <span>Loading...</span>
                </div>
                <div id="robot-details" style="margin-top: 15px;">
                    <!-- Robot status details will be loaded here -->
                </div>
            </div>

            <div class="panel">
                <h2>Recent Health Alerts</h2>
                <div id="health-alerts">
                    Loading health alerts...
                </div>
                <button class="btn btn-primary" onclick="refreshAlerts()">Refresh</button>
            </div>

            <div class="panel">
                <h2>Patient Database</h2>
                <div id="patient-list">
                    Loading patients...
                </div>
                <button class="btn btn-primary" onclick="refreshPatients()">Refresh</button>
            </div>

            <div class="panel">
                <h2>System Errors</h2>
                <div id="error-reports">
                    No errors reported
                </div>
                <button class="btn btn-primary" onclick="refreshErrors()">Refresh</button>
            </div>
        </div>

        <script>
            // Auto-refresh every 30 seconds
            setInterval(function() {
                refreshStatus();
                refreshAlerts();
            }, 30000);

            // Load data on page load
            window.onload = function() {
                refreshStatus();
                refreshAlerts();
                refreshPatients();
                refreshErrors();
            };

            async function refreshStatus() {
                try {
                    const response = await fetch('/api/robot/status');
                    const data = await response.json();
                    updateRobotStatus(data);
                } catch (error) {
                    console.error('Error loading robot status:', error);
                }
            }

            async function refreshAlerts() {
                try {
                    const response = await fetch('/api/health/alerts');
                    const data = await response.json();
                    updateHealthAlerts(data);
                } catch (error) {
                    console.error('Error loading health alerts:', error);
                }
            }

            async function refreshPatients() {
                try {
                    const response = await fetch('/api/patients');
                    const data = await response.json();
                    updatePatients(data);
                } catch (error) {
                    console.error('Error loading patients:', error);
                }
            }

            async function refreshErrors() {
                try {
                    const response = await fetch('/api/errors');
                    const data = await response.json();
                    updateErrors(data);
                } catch (error) {
                    console.error('Error loading errors:', error);
                }
            }

            function updateRobotStatus(status) {
                const statusDiv = document.getElementById('robot-status');
                const detailsDiv = document.getElementById('robot-details');

                if (status.hardware_ready && !status.emergency_stopped) {
                    statusDiv.innerHTML = '<span class="status-indicator status-online"></span>Online - ' + status.current_mode;
                } else if (status.emergency_stopped) {
                    statusDiv.innerHTML = '<span class="status-indicator status-offline"></span>Emergency Stop';
                } else {
                    statusDiv.innerHTML = '<span class="status-indicator status-warning"></span>Hardware Issues';
                }

                detailsDiv.innerHTML = `
                    <p><strong>CPU Usage:</strong> ${status.cpu_usage}%</p>
                    <p><strong>Memory:</strong> ${status.memory_usage}%</p>
                    <p><strong>Temperature:</strong> ${status.temperature}°C</p>
                    <p><strong>Last Update:</strong> <span class="timestamp">${new Date(status.timestamp).toLocaleString()}</span></p>
                `;
            }

            function updateHealthAlerts(alerts) {
                const alertsDiv = document.getElementById('health-alerts');
                if (alerts.length === 0) {
                    alertsDiv.innerHTML = '<p>No recent health alerts</p>';
                    return;
                }

                let html = '';
                alerts.forEach(alert => {
                    const severityClass = alert.severity_level >= 4 ? 'severity-high' :
                                        alert.severity_level >= 2 ? 'severity-medium' : 'severity-low';
                    html += `
                        <div class="health-log ${severityClass}">
                            <strong>Patient:</strong> ${alert.patient_name}<br>
                            <strong>Symptoms:</strong> ${alert.symptoms}<br>
                            <strong>Sentiment:</strong> ${alert.sentiment}<br>
                            <strong>Severity:</strong> ${alert.severity_level}/5<br>
                            <span class="timestamp">${new Date(alert.timestamp).toLocaleString()}</span>
                        </div>
                    `;
                });
                alertsDiv.innerHTML = html;
            }

            function updatePatients(patients) {
                const patientDiv = document.getElementById('patient-list');
                if (patients.length === 0) {
                    patientDiv.innerHTML = '<p>No patients registered</p>';
                    return;
                }

                let html = '<table><tr><th>Name</th><th>Age</th><th>Photos</th><th>Last Seen</th></tr>';
                patients.forEach(patient => {
                    const lastSeen = patient.last_seen ? new Date(patient.last_seen).toLocaleDateString() : 'Never';
                    html += `
                        <tr>
                            <td>${patient.name}</td>
                            <td>${patient.age || 'N/A'}</td>
                            <td>${patient.photo_count}</td>
                            <td>${lastSeen}</td>
                        </tr>
                    `;
                });
                html += '</table>';
                patientDiv.innerHTML = html;
            }

            function updateErrors(errors) {
                const errorDiv = document.getElementById('error-reports');
                if (errors.length === 0) {
                    errorDiv.innerHTML = '<p>No errors reported</p>';
                    return;
                }

                let html = '';
                errors.forEach(error => {
                    html += `
                        <div class="error-report">
                            <strong>${error.component}:</strong> ${error.error_type}<br>
                            <p>${error.message}</p>
                            <span class="timestamp">${new Date(error.timestamp).toLocaleString()}</span>
                        </div>
                    `;
                });
                errorDiv.innerHTML = html;
            }
        </script>
    </body>
    </html>
    """
    return html_content

# API endpoints
@app.get("/api/patients", response_model=List[PatientInfo])
async def get_patients():
    """Get all registered patients"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, age, illness, medications, photo_count, registered_at, last_seen
                FROM patients ORDER BY last_seen DESC
            ''')
            rows = cursor.fetchall()

            patients = []
            for row in rows:
                patients.append(PatientInfo(
                    id=row[0],
                    name=row[1],
                    age=row[2],
                    illness=row[3],
                    medications=row[4],
                    photo_count=row[5],
                    registered_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
                    last_seen=datetime.fromisoformat(row[7]) if row[7] else None
                ))

            return patients

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.get("/api/health/alerts")
async def get_health_alerts():
    """Get recent health alerts requiring doctor attention"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Get alerts from last 24 hours
            yesterday = datetime.now() - timedelta(hours=24)
            cursor.execute('''
                SELECT h.*, p.name as patient_name
                FROM health_logs h
                JOIN patients p ON h.patient_id = p.id
                WHERE h.timestamp >= ? AND h.severity_level >= 2
                ORDER BY h.severity_level DESC, h.timestamp DESC
                LIMIT 20
            ''', (yesterday.isoformat(),))

            rows = cursor.fetchall()
            alerts = []

            for row in rows:
                alerts.append({
                    'id': row[0],
                    'patient_id': row[1],
                    'patient_name': row[8],
                    'symptoms': row[2],
                    'voice_log': row[3],
                    'sentiment': row[4],
                    'severity_level': row[5],
                    'doctor_notified': bool(row[6]),
                    'timestamp': row[7]
                })

            return alerts

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.post("/api/health/log")
async def log_health_incident(health_log: HealthLog):
    """Log a new health incident from robot"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO health_logs
                (patient_id, symptoms, voice_log, sentiment, severity_level, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                health_log.patient_id,
                health_log.symptoms,
                health_log.voice_log,
                health_log.sentiment,
                health_log.severity_level,
                health_log.timestamp.isoformat()
            ))
            conn.commit()

        return {"status": "logged", "id": cursor.lastrowid}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.get("/api/robot/status")
async def get_robot_status():
    """Get current robot status"""
    global latest_robot_status

    if latest_robot_status is None:
        # Return default status if no data available
        return {
            "current_mode": "unknown",
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "temperature": 0.0,
            "hardware_ready": False,
            "emergency_stopped": False,
            "timestamp": datetime.now()
        }

    return latest_robot_status

@app.post("/api/robot/status")
async def update_robot_status(status: RobotStatus):
    """Update robot status from robot controller"""
    global latest_robot_status
    latest_robot_status = status
    return {"status": "updated"}

@app.get("/api/errors")
async def get_error_reports():
    """Get recent error reports"""
    global error_reports
    # Return last 10 errors
    return error_reports[-10:]

@app.post("/api/errors")
async def report_error(error: ErrorReport):
    """Report error from Pi 5 testing"""
    global error_reports
    error_reports.append(error)

    # Keep only last 50 errors
    if len(error_reports) > 50:
        error_reports = error_reports[-50:]

    print(f"🚨 Error reported: {error.component} - {error.message}")
    return {"status": "recorded"}

@app.delete("/api/errors")
async def clear_errors():
    """Clear all error reports"""
    global error_reports
    error_reports.clear()
    return {"status": "cleared"}

if __name__ == "__main__":
    print("🌐 Starting Mars Robot Doctor Dashboard...")
    uvicorn.run(
        "dashboard:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )