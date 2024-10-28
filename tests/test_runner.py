import pytest
import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test-artifacts/test_execution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_test_report(test_results, start_time, end_time):
    """Generate a comprehensive test report"""
    report = {
        'summary': {
            'total_tests': len(test_results),
            'passed': sum(1 for r in test_results if r['outcome'] == 'passed'),
            'failed': sum(1 for r in test_results if r['outcome'] == 'failed'),
            'execution_time': end_time - start_time,
            'timestamp': datetime.now().isoformat()
        },
        'test_cases': test_results
    }
    
    # Create HTML report
    html_report = f"""
    <html>
    <head>
        <title>Test Execution Report</title>
        <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
    </head>
    <body class="bg-dark text-light p-4">
        <div class="container">
            <h1>Test Execution Report</h1>
            <div class="card bg-dark border-secondary mb-4">
                <div class="card-body">
                    <h2>Summary</h2>
                    <p>Total Tests: {report['summary']['total_tests']}</p>
                    <p>Passed: <span class="text-success">{report['summary']['passed']}</span></p>
                    <p>Failed: <span class="text-danger">{report['summary']['failed']}</span></p>
                    <p>Execution Time: {report['summary']['execution_time']:.2f} seconds</p>
                    <p>Timestamp: {report['summary']['timestamp']}</p>
                </div>
            </div>
            
            <h2>Test Cases</h2>
            <div class="list-group">
    """
    
    for test in report['test_cases']:
        status_class = 'text-success' if test['outcome'] == 'passed' else 'text-danger'
        html_report += f"""
            <div class="list-group-item bg-dark border-secondary">
                <h5 class="{status_class}">{test['name']}</h5>
                <p>Duration: {test['duration']:.2f}s</p>
                {'<p class="text-danger">Error: ' + test['error'] + '</p>' if test.get('error') else ''}
                {'<p>Screenshots: ' + '<br>'.join(test['screenshots']) + '</p>' if test.get('screenshots') else ''}
            </div>
        """
    
    html_report += """
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save reports
    os.makedirs('test-artifacts', exist_ok=True)
    with open('test-artifacts/test_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    with open('test-artifacts/test_report.html', 'w') as f:
        f.write(html_report)
    
    return report

def main():
    """Main test runner function"""
    logger.info("Starting test execution")
    start_time = time.time()
    
    # Ensure test artifacts directory exists
    os.makedirs('test-artifacts', exist_ok=True)
    
    # Initialize test results list
    test_results = []
    
    try:
        # Run pytest with detailed output
        pytest_args = [
            '-v',
            '--headed',  # Run in headed mode for screenshots
            '--html=test-artifacts/pytest_report.html',
            '--self-contained-html',
            'tests/test_auth.py',
            'tests/test_messaging.py',
            'tests/test_search.py',
            'tests/test_ui.py'
        ]
        
        # Execute tests and capture results
        result = pytest.main(pytest_args)
        
        # Process results from _pytest.reports
        from _pytest.reports import TestReport
        
        for item in pytest.test_reports if hasattr(pytest, 'test_reports') else []:
            if isinstance(item, TestReport):
                test_result = {
                    'name': item.nodeid,
                    'outcome': item.outcome,
                    'duration': item.duration,
                }
                
                if item.outcome == 'failed':
                    test_result['error'] = str(item.longrepr)
                
                # Find associated screenshots
                test_name = item.nodeid.split('::')[-1]
                screenshots = []
                for file in Path('test-artifacts').glob(f'*{test_name}*.png'):
                    screenshots.append(str(file))
                if screenshots:
                    test_result['screenshots'] = screenshots
                
                test_results.append(test_result)
        
    except Exception as e:
        logger.error(f"Error during test execution: {str(e)}")
        raise
    finally:
        end_time = time.time()
        
        # Generate report
        report = create_test_report(test_results, start_time, end_time)
        
        # Log summary
        logger.info(f"Test execution completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Total tests: {report['summary']['total_tests']}")
        logger.info(f"Passed: {report['summary']['passed']}")
        logger.info(f"Failed: {report['summary']['failed']}")
        
        # Return exit code based on test results
        return 1 if report['summary']['failed'] > 0 else 0

if __name__ == '__main__':
    exit(main())
