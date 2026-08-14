export type RoleName = 'admin' | 'hr' | 'manager' | 'employee';

export interface AuthUser {
  user_id: string;
  email: string;
  role_name: RoleName;
  status: 'active' | 'inactive' | 'locked';
  token_version: number;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Employee {
  employee_id: string;
  user_id: string | null;
  employee_code: string;
  full_name: string;
  phone: string | null;
  avatar_url: string | null;
  department_id: number | null;
  position_id: number | null;
  manager_id: string | null;
  date_of_birth: string | null;
  gender: 'male' | 'female' | 'other' | null;
  address: string | null;
  hire_date: string | null;
  resignation_date: string | null;
  status: 'active' | 'inactive' | 'resigned';
  created_at: string;
  updated_at: string;
}

export interface WorkShift {
  shift_id: number;
  name: string;
  code: string | null;
  start_time: string;
  end_time: string;
  is_overnight: boolean;
  late_threshold_minutes: number;
  early_leave_threshold_minutes: number;
  required_work_minutes: number | null;
  is_active: boolean;
}

export interface CurrentShift {
  assignment_id: number;
  employee_id: string;
  effective_date: string;
  end_date: string | null;
  shift: WorkShift;
}

export interface AttendanceRecord {
  record_id: string;
  employee_id: string;
  work_date: string;
  check_in_time: string | null;
  check_out_time: string | null;
  status: string;
  late_minutes: number;
  early_leave_minutes: number;
  worked_minutes: number;
  source: string;
  notes: string | null;
}

export interface AttendanceSummary {
  total_records: number;
  present_days: number;
  late_days: number;
  absent_days: number;
}

export interface Holiday {
  holiday_id: number;
  name: string;
  holiday_date: string;
  description: string | null;
}

export interface FaceProfile {
  profile_id: string;
  employee_id: string;
  status: 'pending' | 'active' | 'revoked' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface MonthlyReport {
  employee_id: string;
  employee_code: string;
  full_name: string;
  department_id: number | null;
  department_name: string | null;
  year: number;
  month: number;
  total_records: number;
  present_days: number;
  late_days: number;
  early_leave_days: number;
  absent_days: number;
  on_leave_days: number;
  holiday_days: number;
  missing_check_in_days: number;
  missing_check_out_days: number;
  total_worked_minutes: number;
  total_late_minutes: number;
  total_early_leave_minutes: number;
  records: AttendanceRecord[];
}
