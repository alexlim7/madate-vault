#!/usr/bin/env node

/**
 * k6 Script Validator
 * Validates the k6 load testing script syntax and configuration
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
  cyan: '\x1b[36m',
};

function colorize(text, color) {
  return `${colors[color]}${text}${colors.reset}`;
}

function validateScript() {
  console.log(colorize('🔍 Validating k6 Load Test Script', 'bright'));
  console.log(colorize('=' .repeat(40), 'blue'));
  console.log('');

  const scriptFile = path.join(__dirname, 'load_test_mandates.js');
  
  if (!fs.existsSync(scriptFile)) {
    console.error(colorize(`❌ Script file not found: ${scriptFile}`, 'red'));
    return false;
  }

  const scriptContent = fs.readFileSync(scriptFile, 'utf8');
  let issues = [];
  let warnings = [];

  // Check for required imports
  console.log(colorize('📦 Checking imports...', 'cyan'));
  const requiredImports = [
    "import http from 'k6/http'",
    "import { check, sleep } from 'k6'",
    "import { Rate, Trend } from 'k6/metrics'",
  ];
  
  requiredImports.forEach(importStatement => {
    if (scriptContent.includes(importStatement)) {
      console.log(colorize(`  ✅ ${importStatement}`, 'green'));
    } else {
      issues.push(`Missing import: ${importStatement}`);
      console.log(colorize(`  ❌ Missing: ${importStatement}`, 'red'));
    }
  });

  // Check for custom metrics
  console.log(colorize('\n📊 Checking custom metrics...', 'cyan'));
  const customMetrics = [
    'export const errorRate = new Rate',
    'export const mandateCreationLatency = new Trend',
    'export const verificationLatency = new Trend',
  ];
  
  customMetrics.forEach(metric => {
    if (scriptContent.includes(metric)) {
      console.log(colorize(`  ✅ ${metric}`, 'green'));
    } else {
      issues.push(`Missing metric: ${metric}`);
      console.log(colorize(`  ❌ Missing: ${metric}`, 'red'));
    }
  });

  // Check for options configuration
  console.log(colorize('\n⚙️ Checking options configuration...', 'cyan'));
  const optionsChecks = [
    'export const options',
    'constant-arrival-rate',
    'duration: \'1h\'',
    'rate: 2.78',
    'thresholds:',
  ];
  
  optionsChecks.forEach(check => {
    if (scriptContent.includes(check)) {
      console.log(colorize(`  ✅ ${check}`, 'green'));
    } else {
      issues.push(`Missing option: ${check}`);
      console.log(colorize(`  ❌ Missing: ${check}`, 'red'));
    }
  });

  // Check for JWT generation functions
  console.log(colorize('\n🔐 Checking JWT generation functions...', 'cyan'));
  const jwtFunctions = [
    'generateValidJWT',
    'generateExpiredJWT',
    'generateInvalidJWT',
    'generateTamperedJWT',
    'generateMalformedJWT',
  ];
  
  jwtFunctions.forEach(func => {
    if (scriptContent.includes(func)) {
      console.log(colorize(`  ✅ ${func}()`, 'green'));
    } else {
      issues.push(`Missing function: ${func}`);
      console.log(colorize(`  ❌ Missing: ${func}()`, 'red'));
    }
  });

  // Check for test functions
  console.log(colorize('\n🧪 Checking test functions...', 'cyan'));
  const testFunctions = [
    'createMandate',
    'fetchMandate',
    'searchMandates',
    'getAuditLogs',
    'export default function',
    'export function setup',
    'export function teardown',
  ];
  
  testFunctions.forEach(func => {
    if (scriptContent.includes(func)) {
      console.log(colorize(`  ✅ ${func}()`, 'green'));
    } else {
      issues.push(`Missing function: ${func}`);
      console.log(colorize(`  ❌ Missing: ${func}()`, 'red'));
    }
  });

  // Check for configuration variables
  console.log(colorize('\n🔧 Checking configuration...', 'cyan'));
  const configVars = [
    'BASE_URL',
    'TENANT_ID',
    'VALID_JWT_RATIO',
    'issuerDIDs',
    'subjectDIDs',
    'scopes',
    'amountLimits',
  ];
  
  configVars.forEach(config => {
    if (scriptContent.includes(config)) {
      console.log(colorize(`  ✅ ${config}`, 'green'));
    } else {
      issues.push(`Missing configuration: ${config}`);
      console.log(colorize(`  ❌ Missing: ${config}`, 'red'));
    }
  });

  // Check for thresholds
  console.log(colorize('\n🎯 Checking thresholds...', 'cyan'));
  const thresholds = [
    'p(95)<2000',
    'rate<0.1',
    'p(95)<1500',
    'p(95)<1000',
  ];
  
  thresholds.forEach(threshold => {
    if (scriptContent.includes(threshold)) {
      console.log(colorize(`  ✅ ${threshold}`, 'green'));
    } else {
      warnings.push(`Missing threshold: ${threshold}`);
      console.log(colorize(`  ⚠️ Missing: ${threshold}`, 'yellow'));
    }
  });

  // Summary
  console.log(colorize('\n📊 Validation Summary', 'bright'));
  console.log(colorize('=' .repeat(40), 'blue'));
  
  if (issues.length === 0) {
    console.log(colorize('✅ Script validation PASSED', 'green'));
    console.log(colorize('  All required components found', 'green'));
  } else {
    console.log(colorize('❌ Script validation FAILED', 'red'));
    console.log(colorize('  Issues found:', 'red'));
    issues.forEach(issue => {
      console.log(colorize(`    - ${issue}`, 'red'));
    });
  }
  
  if (warnings.length > 0) {
    console.log(colorize('\n⚠️ Warnings:', 'yellow'));
    warnings.forEach(warning => {
      console.log(colorize(`    - ${warning}`, 'yellow'));
    });
  }

  console.log('');
  console.log(colorize('📋 Script Statistics', 'cyan'));
  console.log(colorize('-' .repeat(30), 'cyan'));
  console.log(`Total lines: ${scriptContent.split('\n').length}`);
  console.log(`File size: ${(scriptContent.length / 1024).toFixed(2)} KB`);
  console.log(`Functions defined: ${(scriptContent.match(/function\s+\w+/g) || []).length}`);
  console.log(`Custom metrics: ${(scriptContent.match(/new (Rate|Trend)/g) || []).length}`);
  console.log(`API endpoints: ${(scriptContent.match(/\/api\/v1\//g) || []).length}`);

  return issues.length === 0;
}

// Main execution
if (require.main === module) {
  const isValid = validateScript();
  process.exit(isValid ? 0 : 1);
}

module.exports = { validateScript };
