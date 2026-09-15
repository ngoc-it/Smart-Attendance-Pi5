-- SmartAttendance Database Schema Export (DDL)
-- Dùng để import vào các công cụ như DBeaver, MySQL Workbench, v.v.

CREATE TABLE departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE majors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department_id INTEGER,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    full_name TEXT,
    email TEXT,
    department_id INTEGER,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE semesters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    is_current INTEGER DEFAULT 0
);

CREATE TABLE classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    major_id INTEGER,
    semester_id INTEGER,
    teacher_id INTEGER,
    FOREIGN KEY (major_id) REFERENCES majors(id),
    FOREIGN KEY (semester_id) REFERENCES semesters(id),
    FOREIGN KEY (teacher_id) REFERENCES users(id)
);

CREATE TABLE students (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dob TEXT,
    student_class TEXT,
    status TEXT,
    last_seen TEXT,
    password TEXT
);

CREATE TABLE class_students (
    class_id INTEGER,
    student_id TEXT,
    PRIMARY KEY (class_id, student_id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (student_id) REFERENCES students(id)
);

CREATE TABLE rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    capacity INTEGER,
    has_camera INTEGER DEFAULT 0
);

CREATE TABLE schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER,
    weekday INTEGER,
    start_period_id INTEGER,
    num_periods INTEGER,
    room_id INTEGER,
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

CREATE TABLE class_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER,
    session_date TEXT,
    start_time TEXT,
    end_time TEXT,
    room_id INTEGER,
    status TEXT,
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

CREATE TABLE attendance_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT,
    name TEXT,
    date TEXT,
    time TEXT,
    status TEXT,
    image TEXT,
    room_id INTEGER,
    class_id INTEGER,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (class_id) REFERENCES classes(id)
);

CREATE TABLE periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    start_time TEXT,
    end_time TEXT
);

CREATE TABLE makeup_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER,
    user_id INTEGER,
    requested_date TEXT,
    start_period_id INTEGER,
    num_periods INTEGER,
    room_id INTEGER,
    reason TEXT,
    status TEXT,
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);
