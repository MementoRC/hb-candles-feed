# Performance Alert Notifications Setup

This document explains how to configure performance alert notifications for the Hummingbot Candles Feed project.

## Overview

The performance alert system provides real-time notifications when performance regressions are detected during CI runs or scheduled monitoring. The system integrates with:

- **Slack** - Team notifications
- **Discord** - Community notifications  
- **GitHub Issues** - Automated issue creation for tracking
- **TaskMaster** - Integration with task tracking system

## Alert Types

### 1. Performance Regression Alerts
- Triggered when benchmark performance exceeds configured thresholds
- Runs after successful CI completion
- Creates GitHub issues for tracking

### 2. Real-time Monitoring Alerts
- Scheduled health checks every 4 hours
- Manual testing via workflow dispatch
- Proactive monitoring of system health

## Configuration

### Repository Secrets (Required for Notifications)

Configure these secrets in your GitHub repository settings (`Settings > Secrets and variables > Actions`):

```
SLACK_WEBHOOK_URL     # Slack webhook URL for team notifications
DISCORD_WEBHOOK_URL   # Discord webhook URL for community alerts
```

#### How to get webhook URLs:

**Slack:**
1. Go to https://api.slack.com/messaging/webhooks
2. Create a new app or use existing one
3. Add "Incoming Webhooks" feature
4. Create webhook for your channel
5. Copy the webhook URL

**Discord:**
1. Go to your Discord server settings
2. Navigate to `Integrations > Webhooks`
3. Click `New Webhook`
4. Configure channel and copy webhook URL

### Repository Variables (Optional Thresholds)

Configure these variables in your GitHub repository settings (`Settings > Secrets and variables > Actions > Variables`):

```
PERFORMANCE_ALERT_THRESHOLD_MS    # Absolute threshold in milliseconds (default: 10000)
DEGRADATION_THRESHOLD_PERCENT     # Relative degradation threshold (default: 20)
```

### Default Configuration

If variables are not configured, the system uses these defaults:
- **Absolute Threshold**: 10,000ms (10 seconds)
- **Relative Degradation**: 20% performance regression

## Workflows

### 1. Performance Degradation Alerts (`.github/workflows/performance-alerts.yml`)

**Trigger:** After successful CI completion with benchmark artifacts

**Features:**
- Downloads benchmark results from CI
- Compares against configured thresholds
- Sends Slack/Discord notifications
- Creates GitHub issues with performance tables
- Includes TaskMaster task ID integration
- Retry logic with exponential backoff

**Notification Format:**
```
📉 Performance Regression Detected in owner/repo (Commit: abc1234)
Workflow: https://github.com/owner/repo/actions/runs/123456
Regressions:
- test_network_client_performance: 15000.50 µs (Exceeded absolute threshold of 10000ms)
Associated TaskMaster ID: 10.4
```

### 2. Real-time Performance Monitoring (`.github/workflows/performance-monitoring.yml`)

**Triggers:**
- Scheduled: Every 4 hours
- Manual: Workflow dispatch with test options
- CI Progress: When main CI workflow is in progress

**Features:**
- Health status monitoring
- Configurable threshold overrides
- Force notification testing
- Enhanced message formatting
- Proactive system monitoring

## Testing the System

### Manual Test
1. Go to `Actions > Real-time Performance Monitoring`
2. Click `Run workflow`
3. Enable `Force send test notification`
4. Optionally override threshold
5. Check your Slack/Discord channels for test message

### Threshold Testing
1. Temporarily lower the threshold via repository variables
2. Run benchmark tests that exceed the new threshold
3. Verify notifications are sent
4. Reset threshold to production values

## Notification Channels

### Slack Integration
- Rich formatted messages with color coding
- Structured fields for easy reading
- Timestamp and repository information
- Performance data tables

### Discord Integration  
- Embedded messages with color indicators
- Repository and threshold information
- Timestamp and footer branding
- Community-friendly formatting

### GitHub Issues
- Automatically created for all performance regressions
- Markdown tables with benchmark details
- Links to CI runs and commit information
- TaskMaster integration for task tracking
- Labeled for easy filtering (`performance`, `regression`, `needs-investigation`)

## Error Handling

### Webhook Failures
- Automatic retry with exponential backoff (3 attempts)
- Graceful degradation if webhooks are unavailable
- Detailed logging for troubleshooting
- Fallback to GitHub issues if external notifications fail

### Configuration Issues
- Validates webhook URLs before sending
- Provides clear logs when configuration is missing
- Uses sensible defaults for thresholds
- Graceful handling of malformed configuration

## Integration with Existing Systems

### TaskMaster Integration
- Automatically detects TaskMaster task IDs in commit messages
- Includes task references in notifications and issues
- Pattern: `Task ID.*?(\d+(?:\.\d+)?)`
- Example: "feat: implement Task 10.4 - Performance alerts"

### CI/CD Pipeline Integration
- Seamless integration with existing pytest-benchmark setup
- Uses existing benchmark artifact structure
- Compatible with multi-platform CI matrix
- Preserves existing GitHub issue creation workflow

### Monitoring Infrastructure
- Leverages existing `candles_feed.core.notifications` system
- Compatible with `candles_feed.integration.notifications`
- Uses established performance profiling patterns
- Integrates with existing health check endpoints

## Security Considerations

### Webhook Security
- Webhook URLs stored as repository secrets
- No sensitive data in notification content
- Rate limiting inherent in GitHub Actions execution
- Secure transmission over HTTPS

### Access Control
- Uses GitHub Actions permissions model
- Limited to repository collaborators
- Audit trail in GitHub Actions logs
- No elevation of privileges required

## Troubleshooting

### Notifications Not Sending
1. Verify webhook URLs are configured in repository secrets
2. Check webhook URLs are valid and accessible
3. Review GitHub Actions logs for error messages
4. Test webhooks manually using curl or similar tools

### Performance Alerts Not Triggering
1. Verify benchmark artifacts are being created in CI
2. Check threshold configuration in repository variables
3. Ensure benchmark file structure matches expected format
4. Review CI logs for benchmark execution

### False Positives
1. Adjust `PERFORMANCE_ALERT_THRESHOLD_MS` to appropriate level
2. Consider implementing baseline comparison (future enhancement)
3. Review benchmark test implementation for consistency
4. Monitor over time to establish appropriate thresholds

## Future Enhancements

### Planned Features
- **Baseline Comparison**: Compare against previous runs for relative regression detection
- **Trend Analysis**: Track performance over time with statistical analysis
- **Custom Alert Rules**: More sophisticated alerting logic
- **Notification Templates**: Customizable message formats
- **Integration APIs**: REST endpoints for external monitoring systems

### Configuration Enhancements
- Per-benchmark thresholds
- Time-based threshold adjustments
- Environment-specific configurations
- Advanced filtering rules

## Monitoring Best Practices

1. **Set Realistic Thresholds**: Based on actual performance requirements
2. **Regular Review**: Periodically assess and adjust thresholds
3. **Test Notifications**: Use manual workflow dispatch to verify setup
4. **Monitor Trends**: Watch for gradual performance degradation
5. **Document Changes**: Keep track of threshold adjustments and reasons

This performance monitoring system provides comprehensive coverage of performance-related issues while maintaining flexibility and ease of configuration.