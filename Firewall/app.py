from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
import numpy as np
import os
from datetime import datetime
import json
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)

def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif pd.isna(obj):
        return None
    else:
        return obj

def analyze_file(file_path):
    """Analyze both Excel and CSV files"""
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.csv':
        return analyze_csv_file(file_path)
    elif file_extension in ['.xlsx', '.xls']:
        return analyze_excel_file(file_path)
    else:
        return None, "Unsupported file format"

def analyze_csv_file(file_path):
    """Comprehensive CSV file analysis"""
    try:
        # Read CSV file with different encodings and separators
        df = None
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        separators = [',', ';', '\t', '|']
        
        for encoding in encodings:
            for sep in separators:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, sep=sep)
                    # Check if we got reasonable data
                    if len(df.columns) > 1 or (len(df.columns) == 1 and len(df) > 1):
                        break
                except:
                    continue
            if df is not None and len(df.columns) > 1:
                break
        
        if df is None:
            # Final attempt with default settings
            df = pd.read_csv(file_path)
        
        analysis_results = {
            'file_info': {
                'filename': os.path.basename(file_path),
                'total_sheets': 1,  # CSV has only one "sheet"
                'sheet_names': ['CSV Data'],
                'file_size': os.path.getsize(file_path),
                'file_type': 'CSV'
            },
            'sheets_analysis': {
                'CSV Data': analyze_dataframe(df, 'CSV Data')
            },
            'summary': {
                'total_rows_all_sheets': len(df),
                'total_columns_all_sheets': len(df.columns),
                'average_rows_per_sheet': len(df),
                'average_columns_per_sheet': len(df.columns)
            }
        }
        
        # Convert numpy types to native Python types
        analysis_results = convert_numpy_types(analysis_results)
        
        return analysis_results, None
        
    except Exception as e:
        return None, f"Error analyzing CSV file: {str(e)}"

def analyze_excel_file(file_path):
    """Comprehensive Excel file analysis"""
    try:
        # Read Excel file and get all sheet names
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        
        analysis_results = {
            'file_info': {
                'filename': os.path.basename(file_path),
                'total_sheets': len(sheet_names),
                'sheet_names': sheet_names,
                'file_size': os.path.getsize(file_path),
                'file_type': 'Excel'
            },
            'sheets_analysis': {},
            'summary': {}
        }
        
        total_rows = 0
        total_columns = 0
        
        # Analyze each sheet
        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheet_analysis = analyze_dataframe(df, sheet_name)
                analysis_results['sheets_analysis'][sheet_name] = sheet_analysis
                
                total_rows += len(df)
                total_columns += len(df.columns)
                
            except Exception as e:
                analysis_results['sheets_analysis'][sheet_name] = {
                    'error': f"Could not analyze sheet: {str(e)}"
                }
        
        # Overall summary
        analysis_results['summary'] = {
            'total_rows_all_sheets': total_rows,
            'total_columns_all_sheets': total_columns,
            'average_rows_per_sheet': total_rows / len(sheet_names) if sheet_names else 0,
            'average_columns_per_sheet': total_columns / len(sheet_names) if sheet_names else 0
        }
        
        # Convert numpy types to native Python types
        analysis_results = convert_numpy_types(analysis_results)
        
        return analysis_results, None
        
    except Exception as e:
        return None, f"Error analyzing Excel file: {str(e)}"

def analyze_dataframe(df, sheet_name):
    """Analyze individual DataFrame/sheet"""
    analysis = {
        'basic_info': {
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': list(df.columns),
            'memory_usage': df.memory_usage(deep=True).sum()
        },
        'data_quality': {
            'total_missing_values': df.isnull().sum().sum(),
            'missing_values_per_column': df.isnull().sum().to_dict(),
            'duplicate_rows': df.duplicated().sum(),
            'data_types': df.dtypes.astype(str).to_dict()
        },
        'column_analysis': {},
        'sample_data': {}
    }
    
    # Analyze each column
    for column in df.columns:
        col_analysis = analyze_column(df[column], column)
        analysis['column_analysis'][column] = col_analysis
    
    # Sample data (first 5 rows)
    sample_data = df.head().fillna('').to_dict('records')
    analysis['sample_data'] = sample_data
    
    return analysis

def analyze_column(series, column_name):
    """Analyze individual column"""
    analysis = {
        'data_type': str(series.dtype),
        'non_null_count': series.count(),
        'null_count': series.isnull().sum(),
        'unique_values': series.nunique(),
        'memory_usage': series.memory_usage(deep=True)
    }
    
    # Numeric analysis
    if pd.api.types.is_numeric_dtype(series):
        non_null_series = series.dropna()
        if not non_null_series.empty:
            analysis['numeric_stats'] = {
                'mean': non_null_series.mean(),
                'median': non_null_series.median(),
                'std': non_null_series.std(),
                'min': non_null_series.min(),
                'max': non_null_series.max(),
                'quartiles': {
                    'Q1': non_null_series.quantile(0.25),
                    'Q3': non_null_series.quantile(0.75)
                }
            }
    
    # Text analysis
    elif pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
        non_null_series = series.dropna()
        if not non_null_series.empty:
            str_lengths = non_null_series.astype(str).str.len()
            analysis['text_stats'] = {
                'average_length': str_lengths.mean(),
                'max_length': str_lengths.max(),
                'min_length': str_lengths.min(),
                'most_common_values': non_null_series.value_counts().head(5).to_dict()
            }
    
    # Date analysis
    elif pd.api.types.is_datetime64_any_dtype(series):
        non_null_series = series.dropna()
        if not non_null_series.empty:
            analysis['date_stats'] = {
                'earliest_date': non_null_series.min().strftime('%Y-%m-%d %H:%M:%S'),
                'latest_date': non_null_series.max().strftime('%Y-%m-%d %H:%M:%S'),
                'date_range_days': (non_null_series.max() - non_null_series.min()).days
            }
    
    # Top values for any column type
    if series.count() > 0:
        top_values = series.value_counts().head(10)
        analysis['top_values'] = top_values.to_dict()
    
    return analysis

def generate_analysis_report(analysis_results, output_dir):
    """Generate comprehensive analysis report"""
    report_path = os.path.join(output_dir, 'file_analysis_report.xlsx')
    
    with pd.ExcelWriter(report_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Create formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # File overview sheet
        file_info = analysis_results['file_info']
        overview_data = [
            ['Metric', 'Value'],
            ['Filename', file_info['filename']],
            ['File Type', file_info['file_type']],
            ['Total Sheets/Tables', file_info['total_sheets']],
            ['File Size (bytes)', file_info['file_size']],
            ['Total Rows', analysis_results['summary']['total_rows_all_sheets']],
            ['Total Columns', analysis_results['summary']['total_columns_all_sheets']],
            ['Average Rows per Sheet', f"{analysis_results['summary']['average_rows_per_sheet']:.2f}"],
            ['Average Columns per Sheet', f"{analysis_results['summary']['average_columns_per_sheet']:.2f}"]
        ]
        
        overview_df = pd.DataFrame(overview_data[1:], columns=overview_data[0])
        overview_df.to_excel(writer, sheet_name='File Overview', index=False)
        
        # Sheet names overview
        sheet_names_data = []
        for i, sheet_name in enumerate(file_info['sheet_names'], 1):
            sheet_info = analysis_results['sheets_analysis'].get(sheet_name, {})
            if 'error' not in sheet_info:
                basic_info = sheet_info.get('basic_info', {})
                sheet_names_data.append([
                    i,
                    sheet_name,
                    basic_info.get('rows', 0),
                    basic_info.get('columns', 0),
                    basic_info.get('memory_usage', 0)
                ])
        
        if sheet_names_data:
            sheets_df = pd.DataFrame(sheet_names_data, columns=[
                'Sheet #', 'Sheet Name', 'Rows', 'Columns', 'Memory Usage (bytes)'
            ])
            sheets_df.to_excel(writer, sheet_name='Sheets Overview', index=False)
        
        # Detailed analysis for each sheet
        for sheet_name, sheet_analysis in analysis_results['sheets_analysis'].items():
            if 'error' in sheet_analysis:
                continue
                
            # Clean sheet name for Excel sheet naming
            clean_sheet_name = sheet_name.replace('/', '_').replace('\\', '_')[:31]
            
            # Basic info
            basic_info = sheet_analysis['basic_info']
            data_quality = sheet_analysis['data_quality']
            
            sheet_summary = [
                ['Metric', 'Value'],
                ['Sheet Name', sheet_name],
                ['Rows', basic_info['rows']],
                ['Columns', basic_info['columns']],
                ['Memory Usage (bytes)', basic_info['memory_usage']],
                ['Total Missing Values', data_quality['total_missing_values']],
                ['Duplicate Rows', data_quality['duplicate_rows']],
                ['', ''],
                ['Column Analysis', '']
            ]
            
            # Column analysis
            for col_name, col_analysis in sheet_analysis['column_analysis'].items():
                sheet_summary.append([f'Column: {col_name}', ''])
                sheet_summary.append(['  Data Type', col_analysis['data_type']])
                sheet_summary.append(['  Non-null Count', col_analysis['non_null_count']])
                sheet_summary.append(['  Unique Values', col_analysis['unique_values']])
                
                # Add numeric stats if available
                if 'numeric_stats' in col_analysis:
                    stats = col_analysis['numeric_stats']
                    sheet_summary.append(['  Mean', f"{stats['mean']:.2f}"])
                    sheet_summary.append(['  Median', f"{stats['median']:.2f}"])
                    sheet_summary.append(['  Std Dev', f"{stats['std']:.2f}"])
                    sheet_summary.append(['  Min', f"{stats['min']:.2f}"])
                    sheet_summary.append(['  Max', f"{stats['max']:.2f}"])
                
                # Add text stats if available
                elif 'text_stats' in col_analysis:
                    stats = col_analysis['text_stats']
                    sheet_summary.append(['  Avg Length', f"{stats['average_length']:.2f}"])
                    sheet_summary.append(['  Max Length', stats['max_length']])
                    sheet_summary.append(['  Min Length', stats['min_length']])
                
                sheet_summary.append(['', ''])
            
            summary_df = pd.DataFrame(sheet_summary[1:], columns=sheet_summary[0])
            summary_df.to_excel(writer, sheet_name=f'{clean_sheet_name}_Analysis', index=False)
            
            # Sample data
            if sheet_analysis['sample_data']:
                sample_df = pd.DataFrame(sheet_analysis['sample_data'])
                sample_df.to_excel(writer, sheet_name=f'{clean_sheet_name}_Sample', index=False)
    
    return report_path

@app.route('/')
def home():
    return render_template('excel_analyzer.html')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'excelfile' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        uploaded_file = request.files['excelfile']
        if uploaded_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        allowed_extensions = ['.xlsx', '.xls', '.csv']
        file_extension = os.path.splitext(uploaded_file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            return jsonify({'error': 'Please upload a valid file (.xlsx, .xls, or .csv)'}), 400
        
        # Save uploaded file
        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, uploaded_file.filename)
        uploaded_file.save(file_path)
        
        # Analyze file
        analysis_results, error = analyze_file(file_path)
        
        if error:
            return jsonify({'error': error}), 400
        
        # Generate report
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)
        report_path = generate_analysis_report(analysis_results, output_dir)
        
        return send_file(report_path, as_attachment=True)
        
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    """API endpoint for file analysis without file download"""
    try:
        if 'excelfile' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        uploaded_file = request.files['excelfile']
        if uploaded_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        allowed_extensions = ['.xlsx', '.xls', '.csv']
        file_extension = os.path.splitext(uploaded_file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            return jsonify({'error': 'Please upload a valid file (.xlsx, .xls, or .csv)'}), 400
        
        # Save uploaded file
        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, uploaded_file.filename)
        uploaded_file.save(file_path)
        
        # Analyze file
        analysis_results, error = analyze_file(file_path)
        
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify(analysis_results)
        
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download generated report"""
    try:
        return send_file(os.path.join('output', filename), as_attachment=True)
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 404

if __name__ == '__main__':
    app.run(debug=True)