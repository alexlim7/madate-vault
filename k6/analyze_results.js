#!/usr/bin/env node

/**
 * k6 Load Test Results Analyzer
 * Analyzes the results from the Mandate Vault load test
 */

const fs = require('fs');
const path = require('path');

// ANSI color codes
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

function colorize(text, color) {
  return `${colors[color]}${text}${colors.reset}`;
}

function formatNumber(num, decimals = 2) {
  return typeof num === 'number' ? num.toFixed(decimals) : 'N/A';
}

function formatDuration(ms) {
  if (ms < 1000) return `${formatNumber(ms)}ms`;
  if (ms < 60000) return `${formatNumber(ms / 1000)}s`;
  return `${formatNumber(ms / 60000)}m`;
}

function calculatePercentile(values, percentile) {
  if (!values || values.length === 0) return 0;
  const sorted = values.sort((a, b) => a - b);
  const index = Math.ceil((percentile / 100) * sorted.length) - 1;
  return sorted[Math.max(0, index)];
}

function analyzeResults(jsonFile) {
  console.log(colorize('📊 Mandate Vault Load Test Results Analysis', 'bright'));
  console.log(colorize('=' .repeat(50), 'blue'));
  console.log('');

  if (!fs.existsSync(jsonFile)) {
    console.error(colorize(`❌ Results file not found: ${jsonFile}`, 'red'));
    process.exit(1);
  }

  const data = JSON.parse(fs.readFileSync(jsonFile, 'utf8'));
  
  // Extract metrics
  const metrics = data.metrics || {};
  
  // Calculate key metrics
  const totalRequests = metrics.http_reqs?.count || 0;
  const totalErrors = metrics.http_req_failed?.count || 0;
  const errorRate = totalRequests > 0 ? (totalErrors / totalRequests) * 100 : 0;
  
  const avgResponseTime = metrics.http_req_duration?.avg || 0;
  const p95ResponseTime = metrics.http_req_duration?.['p(95)'] || 0;
  const p99ResponseTime = metrics.http_req_duration?.['p(99)'] || 0;
  const maxResponseTime = metrics.http_req_duration?.max || 0;
  
  const avgMandateCreationTime = metrics.mandate_creation_latency?.avg || 0;
  const p95MandateCreationTime = metrics.mandate_creation_latency?.['p(95)'] || 0;
  
  const avgVerificationTime = metrics.verification_latency?.avg || 0;
  const p95VerificationTime = metrics.verification_latency?.['p(95)'] || 0;
  
  const throughput = metrics.http_reqs?.rate || 0;
  const dataReceived = metrics.data_received?.count || 0;
  const dataSent = metrics.data_sent?.count || 0;

  // Test duration
  const startTime = new Date(data.start_time);
  const endTime = new Date(data.end_time);
  const duration = endTime - startTime;

  // Display results
  console.log(colorize('📈 Overall Performance', 'cyan'));
  console.log(colorize('-' .repeat(30), 'cyan'));
  console.log(`Total Requests: ${colorize(totalRequests.toLocaleString(), 'green')}`);
  console.log(`Test Duration: ${colorize(formatDuration(duration), 'yellow')}`);
  console.log(`Throughput: ${colorize(formatNumber(throughput, 1), 'green')} req/s`);
  console.log(`Total Errors: ${colorize(totalErrors.toLocaleString(), 'red')}`);
  console.log(`Error Rate: ${colorize(formatNumber(errorRate, 2), errorRate > 10 ? 'red' : 'green')}%`);
  console.log('');

  console.log(colorize('⏱️ Response Time Metrics', 'cyan'));
  console.log(colorize('-' .repeat(30), 'cyan'));
  console.log(`Average Response Time: ${colorize(formatDuration(avgResponseTime), 'yellow')}`);
  console.log(`95th Percentile: ${colorize(formatDuration(p95ResponseTime), 'yellow')}`);
  console.log(`99th Percentile: ${colorize(formatDuration(p99ResponseTime), 'yellow')}`);
  console.log(`Maximum Response Time: ${colorize(formatDuration(maxResponseTime), 'yellow')}`);
  console.log('');

  console.log(colorize('🎯 Mandate-Specific Metrics', 'cyan'));
  console.log(colorize('-' .repeat(30), 'cyan'));
  console.log(`Average Mandate Creation: ${colorize(formatDuration(avgMandateCreationTime), 'yellow')}`);
  console.log(`95th Percentile Creation: ${colorize(formatDuration(p95MandateCreationTime), 'yellow')}`);
  console.log(`Average Verification Time: ${colorize(formatDuration(avgVerificationTime), 'yellow')}`);
  console.log(`95th Percentile Verification: ${colorize(formatDuration(p95VerificationTime), 'yellow')}`);
  console.log('');

  console.log(colorize('📊 Data Transfer', 'cyan'));
  console.log(colorize('-' .repeat(30), 'cyan'));
  console.log(`Data Sent: ${colorize(formatBytes(dataSent), 'blue')}`);
  console.log(`Data Received: ${colorize(formatBytes(dataReceived), 'blue')}`);
  console.log('');

  // Threshold analysis
  console.log(colorize('🎯 Threshold Analysis', 'cyan'));
  console.log(colorize('-' .repeat(30), 'cyan'));
  
  const thresholds = data.thresholds || {};
  let passedThresholds = 0;
  let totalThresholds = 0;
  
  Object.entries(thresholds).forEach(([name, result]) => {
    totalThresholds++;
    const passed = result.ok;
    if (passed) passedThresholds++;
    
    const status = passed ? colorize('✅ PASS', 'green') : colorize('❌ FAIL', 'red');
    console.log(`${status} ${name}: ${result.threshold}`);
  });
  
  console.log('');
  console.log(`Thresholds Passed: ${colorize(passedThresholds, 'green')}/${colorize(totalThresholds, 'blue')}`);
  console.log('');

  // Performance assessment
  console.log(colorize('🏆 Performance Assessment', 'cyan'));
  console.log(colorize('-' .repeat(30), 'cyan'));
  
  let performanceGrade = 'A';
  let issues = [];
  
  if (errorRate > 5) {
    performanceGrade = 'C';
    issues.push('High error rate');
  } else if (errorRate > 1) {
    performanceGrade = 'B';
    issues.push('Moderate error rate');
  }
  
  if (p95ResponseTime > 2000) {
    performanceGrade = performanceGrade === 'A' ? 'B' : 'C';
    issues.push('High p95 response time');
  }
  
  if (p95MandateCreationTime > 1500) {
    performanceGrade = performanceGrade === 'A' ? 'B' : 'C';
    issues.push('High mandate creation latency');
  }
  
  if (throughput < 2) {
    performanceGrade = performanceGrade === 'A' ? 'B' : 'C';
    issues.push('Low throughput');
  }
  
  const gradeColor = performanceGrade === 'A' ? 'green' : performanceGrade === 'B' ? 'yellow' : 'red';
  console.log(`Performance Grade: ${colorize(performanceGrade, gradeColor)}`);
  
  if (issues.length > 0) {
    console.log(`Issues Found: ${colorize(issues.join(', '), 'yellow')}`);
  } else {
    console.log(colorize('✅ No significant performance issues detected', 'green'));
  }
  
  console.log('');

  // Recommendations
  console.log(colorize('💡 Recommendations', 'cyan'));
  console.log(colorize('-' .repeat(30), 'cyan'));
  
  if (errorRate > 10) {
    console.log('🔧 High error rate detected:');
    console.log('  - Check API server logs for errors');
    console.log('  - Verify database connectivity');
    console.log('  - Consider increasing server resources');
    console.log('');
  }
  
  if (p95ResponseTime > 2000) {
    console.log('⚡ High response times detected:');
    console.log('  - Optimize database queries');
    console.log('  - Consider caching mechanisms');
    console.log('  - Scale horizontally if needed');
    console.log('');
  }
  
  if (throughput < 2) {
    console.log('📈 Low throughput detected:');
    console.log('  - Check for bottlenecks in the system');
    console.log('  - Optimize JWT verification process');
    console.log('  - Consider async processing');
    console.log('');
  }
  
  if (issues.length === 0) {
    console.log(colorize('🎉 Excellent performance! System is handling load well.', 'green'));
    console.log('  - Consider increasing load to find breaking point');
    console.log('  - Monitor for memory leaks during sustained load');
  }
  
  console.log('');
  console.log(colorize('📋 Summary', 'bright'));
  console.log(colorize('=' .repeat(50), 'blue'));
  console.log(`Test completed with ${colorize(totalRequests.toLocaleString(), 'green')} requests`);
  console.log(`Error rate: ${colorize(formatNumber(errorRate, 2) + '%', errorRate > 10 ? 'red' : 'green')}`);
  console.log(`P95 latency: ${colorize(formatDuration(p95ResponseTime), 'yellow')}`);
  console.log(`Throughput: ${colorize(formatNumber(throughput, 1) + ' req/s', 'green')}`);
  console.log(`Performance grade: ${colorize(performanceGrade, gradeColor)}`);
  console.log('');
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Main execution
function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.error(colorize('Usage: node analyze_results.js <results.json>', 'red'));
    console.error(colorize('Example: node analyze_results.js k6/results/load_test_results_20240101_120000.json', 'yellow'));
    process.exit(1);
  }
  
  const resultsFile = args[0];
  analyzeResults(resultsFile);
}

if (require.main === module) {
  main();
}
