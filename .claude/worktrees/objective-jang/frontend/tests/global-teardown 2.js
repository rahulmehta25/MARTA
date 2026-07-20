/**
 * Global teardown for Playwright tests
 * Runs once after all test files complete
 */
async function globalTeardown() {
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('🏁 MARTA Application E2E Test Suite Complete');
  
  // Log test results summary location
  console.log('📊 Test results available in:');
  console.log('   • HTML Report: ./playwright-report/index.html');
  console.log('   • JSON Results: ./test-results/results.json');
  console.log('   • JUnit XML: ./test-results/results.xml');
  
  // Clean up any temporary files if needed
  try {
    // Add cleanup logic here if needed in the future
    console.log('🧹 Cleanup completed successfully');
  } catch (error) {
    console.error('⚠️ Cleanup warning:', error.message);
  }
  
  console.log('✨ All tests completed - thank you for testing MARTA!');
}

export default globalTeardown;