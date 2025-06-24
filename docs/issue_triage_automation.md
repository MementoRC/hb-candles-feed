# Intelligent Issue Triage and Labeling System

This document explains the comprehensive automated issue triage and labeling system for the Hummingbot Candles Feed project.

## Overview

The intelligent issue triage system provides automated classification, prioritization, and assignment of GitHub issues and pull requests using advanced content analysis and machine learning techniques.

## System Architecture

### Core Components

1. **Intelligent Issue Triage Workflow** (`.github/workflows/intelligent-issue-triage.yml`)
   - Advanced content analysis with confidence scoring
   - Multi-factor priority assessment
   - Component classification based on technical content
   - Severity analysis for different issue types
   - Assignee recommendations
   - Comprehensive reporting and metrics

2. **Enhanced Automation Workflow** (`.github/workflows/enhanced-automation.yml`)
   - Basic keyword-based labeling
   - Review assignment based on file changes
   - Stale issue management
   - TaskMaster integration

3. **Issue Templates** (`.github/ISSUE_TEMPLATE/`)
   - Structured forms for bug reports, feature requests, and documentation
   - Automatic labeling and assignment
   - Pre-submission validation

## Triage Logic and Rules

### Priority Classification

The system uses a sophisticated multi-factor approach to determine issue priority:

#### P0-Critical (Immediate Action Required)
**Automatic Triggers:**
- Keywords: `critical`, `blocker`, `urgent`, `panic`, `crash`, `data loss`, `security vulnerability`
- Error patterns: `segmentation fault`, `out of memory`, `critical exception`
- Impact indicators: `production down`, `trading stopped`, `complete failure`

**Confidence Scoring:**
- Multiple critical keywords: 95-100%
- Single critical keyword + error pattern: 85-95%
- Critical keyword + high impact: 80-90%

#### P1-High (Next Sprint Priority)
**Automatic Triggers:**
- Keywords: `high impact`, `severe`, `major bug`, `exploit`, `performance regression`
- Error patterns: `connection failed`, `timeout`, `api error`, `rate limit exceeded`
- Impact indicators: `affects multiple users`, `trading degraded`, `significant delay`

**Confidence Scoring:**
- Multiple high-priority indicators: 80-90%
- High keyword + technical evidence: 70-85%
- High impact with user reports: 75-85%

#### P2-Medium (Standard Priority)
**Automatic Triggers:**
- Keywords: `bug`, `error`, `fail`, `incorrect behavior`, `needs fix`
- Error patterns: `warning`, `validation failed`, `unexpected result`
- Impact indicators: `single user affected`, `workaround available`

#### P3-Low (Future Consideration)
**Automatic Triggers:**
- Keywords: `minor bug`, `trivial`, `cosmetic`, `typo`, `suggestion`, `enhancement`
- Patterns: `ui issue`, `documentation`, `code style`

### Component Classification

#### Exchange Adapters
**Detection Patterns:**
- File paths: `candles_feed/adapters/`, `tests/*/adapters/`
- Keywords: `binance`, `coinbase`, `kraken`, `bybit`, `gate.io`, `okx`, `kucoin`, `mexc`, `hyperliquid`, `ascendex`
- Error patterns: `adapter failed`, `exchange api`, `connection error`

#### Core Engine
**Detection Patterns:**
- File paths: `candles_feed/core/`, `tests/*/core/`
- Keywords: `candles feed`, `data processor`, `network client`, `collection strategy`
- Error patterns: `core module`, `engine failed`, `data processing`

#### Network & Connectivity
**Detection Patterns:**
- Keywords: `network`, `connection`, `timeout`, `ssl`, `websocket`, `rest api`
- Error patterns: `connection refused`, `timeout`, `certificate error`

#### Testing & CI/CD
**Detection Patterns:**
- File paths: `tests/`, `.github/workflows/`, `pyproject.toml`
- Keywords: `test failure`, `ci failed`, `pipeline`, `workflow`

#### Documentation
**Detection Patterns:**
- File paths: `docs/`, `README.md`, `*.md`
- Keywords: `documentation`, `docs`, `readme`, `guide`, `tutorial`

### Severity Assessment

#### Bug Severity
- **Critical**: System unusable, data loss, security issues
- **High**: Major functionality broken, significant performance impact
- **Medium**: Feature partially working, minor performance impact
- **Low**: Cosmetic issues, minor inconveniences

#### Feature Impact
- **High**: Core functionality enhancement, significant user value
- **Medium**: Useful addition, moderate user value
- **Low**: Nice-to-have, minimal user impact

### Assignee Recommendation Engine

#### Expertise Mapping
```yaml
Core Components:
  - candles_feed/core/: ["MementoRC"]
  - candles_feed/integration/: ["MementoRC"]

Exchange Adapters:
  - candles_feed/adapters/binance/: ["MementoRC"]
  - candles_feed/adapters/coinbase_advanced_trade/: ["MementoRC"]
  - candles_feed/adapters/kraken/: ["MementoRC"]

Testing & QA:
  - tests/: ["MementoRC"]
  - performance testing: ["MementoRC"]

CI/CD & DevOps:
  - .github/workflows/: ["MementoRC"]
  - deployment: ["MementoRC"]

Documentation:
  - docs/: ["MementoRC"]
  - README.md: ["MementoRC"]
```

#### Assignment Logic
1. **File-based Assignment**: Analyze file paths in PR for automatic reviewer assignment
2. **Expertise Matching**: Match issue content to expert knowledge areas
3. **Workload Balancing**: Consider current assignee workload (future enhancement)
4. **Availability**: Check contributor availability status (future enhancement)

## Advanced Features

### Confidence Scoring System

Each automated decision includes a confidence score (0-100%):

- **90-100%**: High confidence - automatic action
- **70-89%**: Medium confidence - automatic action with human review flag
- **50-69%**: Low confidence - suggest labels for human review
- **0-49%**: Very low confidence - flag for manual triage

### Content Analysis Techniques

#### Natural Language Processing
- **Keyword Extraction**: Technical terms, error patterns, severity indicators
- **Sentiment Analysis**: Urgency detection from user language
- **Context Understanding**: Relationship between title and description

#### Technical Pattern Recognition
- **Error Log Analysis**: Stack traces, error codes, failure patterns
- **Code Reference Detection**: File paths, function names, API endpoints
- **Environment Detection**: OS, version, configuration details

#### Impact Assessment
- **User Count Estimation**: Single user vs. multiple users affected
- **Business Impact**: Trading disruption, revenue impact, user experience
- **Technical Complexity**: Implementation difficulty, risk assessment

### Integration Capabilities

#### TaskMaster AI Integration
- **Automatic Detection**: Scan issue content for TaskMaster task IDs
- **Bidirectional Linking**: Link issues to TaskMaster tasks and vice versa
- **Progress Tracking**: Update TaskMaster when issues are resolved
- **Dependency Mapping**: Identify task dependencies from issue relationships

#### External Tool Integration
- **Slack/Discord Notifications**: Alert relevant teams about high-priority issues
- **JIRA Synchronization**: Sync issues with enterprise project management (future)
- **Monitoring Integration**: Link performance alerts to issue creation
- **Repository Insights**: Feed triage data into repository health metrics

### Metrics and Analytics

#### Triage Performance Metrics
- **Accuracy Rate**: Percentage of correctly classified issues
- **Processing Time**: Average time from issue creation to classification
- **Human Override Rate**: Percentage of automated decisions overridden
- **Confidence Distribution**: Distribution of confidence scores

#### Issue Lifecycle Metrics
- **Time to First Response**: Average response time by priority
- **Resolution Time**: Average time to close by category
- **Reopened Issue Rate**: Percentage of issues reopened after closure
- **Escalation Rate**: Issues escalated to higher priority

#### Repository Health Indicators
- **Issue Velocity**: Creation vs. resolution rate
- **Priority Distribution**: Balance of issue priorities
- **Component Health**: Issue concentration by component
- **Contributor Engagement**: Response and resolution rates by assignee

## Configuration and Customization

### Repository Variables

Configure these in GitHub repository settings (`Settings > Secrets and variables > Actions > Variables`):

```yaml
TRIAGE_CONFIDENCE_THRESHOLD: 70      # Minimum confidence for automatic action
ENABLE_AUTO_ASSIGNMENT: true        # Enable automatic assignee suggestions
ENABLE_PRIORITY_ESCALATION: true    # Enable priority escalation alerts
TRIAGE_NOTIFICATION_CHANNEL: slack  # Primary notification channel
```

### Repository Secrets

```yaml
SLACK_TRIAGE_WEBHOOK: <webhook_url>     # Slack webhook for triage notifications
DISCORD_TRIAGE_WEBHOOK: <webhook_url>   # Discord webhook for alerts
TASKMASTER_API_KEY: <api_key>          # TaskMaster integration (future)
```

### Customizing Classification Rules

#### Priority Keywords
Edit the `priorityMap` in `.github/workflows/intelligent-issue-triage.yml`:

```javascript
const priorityMap = {
  'priority/P0-Critical': ['critical', 'blocker', 'urgent', 'panic'],
  'priority/P1-High': ['high impact', 'severe', 'major bug'],
  'priority/P2-Medium': ['bug', 'error', 'fail', 'incorrect'],
  'priority/P3-Low': ['minor bug', 'trivial', 'cosmetic', 'typo']
};
```

#### Component Detection
Customize the `componentMap` for your project structure:

```javascript
const componentMap = {
  'component/adapters': ['adapter', 'exchange', 'binance', 'coinbase'],
  'component/core': ['core', 'engine', 'processor', 'network'],
  'component/testing': ['test', 'pytest', 'benchmark', 'ci']
};
```

## Workflow Triggers

### Automatic Triggers
- **Issue Opened**: Full triage analysis and classification
- **Issue Edited**: Re-analyze content for updated classification
- **PR Opened**: Reviewer assignment and area classification
- **Scheduled**: Daily triage review and metrics collection

### Manual Triggers
- **Workflow Dispatch**: Manual triage run with custom parameters
- **Comment Commands**: Issue commands like `/retriage`, `/escalate`
- **Label Changes**: Re-evaluate when labels are manually modified

## Monitoring and Troubleshooting

### Workflow Logs
Monitor triage decisions in GitHub Actions logs:
- Classification confidence scores
- Applied labels and reasoning
- Error handling and fallbacks
- Performance metrics

### Common Issues

#### Low Confidence Scores
**Problem**: Issues consistently getting low confidence scores
**Solution**: 
- Review and expand keyword dictionaries
- Adjust confidence thresholds
- Add more technical patterns

#### Incorrect Classifications
**Problem**: Issues misclassified by automation
**Solution**:
- Analyze misclassified examples
- Update pattern matching rules
- Add negative keywords to exclude false positives

#### Missing Assignments
**Problem**: Issues not getting assigned automatically
**Solution**:
- Check expertise mapping configuration
- Verify contributor permissions
- Review file path patterns

### Performance Optimization

#### Reducing API Calls
- Batch operations where possible
- Cache frequently accessed data
- Use conditional requests with ETags

#### Improving Processing Speed
- Optimize regex patterns
- Reduce redundant analysis
- Parallelize independent operations

## Best Practices

### Content Guidelines for Users
1. **Use Descriptive Titles**: Include component and issue type
2. **Provide Context**: Environment details, steps to reproduce
3. **Include Logs**: Error messages and stack traces
4. **Specify Impact**: Number of users affected, business impact

### Maintenance Guidelines
1. **Regular Review**: Weekly review of automated decisions
2. **Pattern Updates**: Monthly update of classification patterns
3. **Performance Monitoring**: Track accuracy and response times
4. **User Feedback**: Collect feedback on triage quality

### Integration Guidelines
1. **Gradual Rollout**: Start with low-confidence suggestions
2. **Human Oversight**: Maintain human review for critical issues
3. **Continuous Learning**: Use feedback to improve patterns
4. **Documentation**: Keep triage rules well-documented

## Future Enhancements

### Machine Learning Integration
- **Natural Language Processing**: Advanced text classification
- **Historical Learning**: Learn from past triage decisions
- **Predictive Analytics**: Predict issue resolution time and effort

### Advanced Automation
- **Smart Routing**: Route issues to appropriate team channels
- **Duplicate Detection**: Identify and link duplicate issues
- **Impact Prediction**: Predict business impact of issues

### Enterprise Features
- **SLA Monitoring**: Track service level agreement compliance
- **Cost Analysis**: Estimate resolution costs and resource needs
- **Risk Assessment**: Identify security and stability risks

This intelligent triage system provides a foundation for efficient issue management while maintaining flexibility for customization and continuous improvement.