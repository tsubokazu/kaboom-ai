# N8N Configuration for Kaboom API Integration

## Service Account Setup

**Service Account**: `n8n-service-account@kaboom-472705.iam.gserviceaccount.com`
**Key File**: `n8n-service-account-key.json`

## Permissions Granted

- `roles/secretmanager.secretAccessor` - Secret Manager から認証情報取得
- `roles/run.invoker` - Cloud Run API 呼び出し

## N8N Workflow Configuration

### 1. Google Cloud Credentials Node
- **Authentication**: Service Account
- **Service Account Key**: `n8n-service-account-key.json` の内容を設定

### 2. Secret Manager Access
Secret Manager から認証トークンを取得する例：

```javascript
// Google Cloud Secret Manager Node
{
  "projectId": "kaboom-472705",
  "secretName": "ingest-api-token",
  "version": "latest"
}
```

### 3. HTTP Request Node (Daily Ingest)
```javascript
{
  "method": "POST",
  "url": "https://kaboom-api-657734233816.asia-northeast1.run.app/api/v1/ingest/run-daily",
  "headers": {
    "X-Ingest-Token": "{{ $node['Secret Manager'].json['payload'] }}",
    "Content-Type": "application/json"
  },
  "body": {
    "intervals": {
      "1m": 2,
      "5m": 5,
      "1d": 730
    }
  }
}
```

### 4. Job Status Monitoring
```javascript
{
  "method": "GET",
  "url": "https://kaboom-api-657734233816.asia-northeast1.run.app/api/v1/ingest/jobs/{{ $node['Daily Ingest'].json['job_id'] }}",
  "headers": {
    "X-Ingest-Token": "{{ $node['Secret Manager'].json['payload'] }}"
  }
}
```

## Cron Schedule Examples

- **Daily**: `0 0 * * *` (毎日午前0時)
- **Business Days**: `0 0 * * 1-5` (平日のみ)
- **After Market Close**: `0 15 * * 1-5` (平日午後3時)

## Notification Setup

### Slack Notification (Success)
```javascript
{
  "channel": "#trading-alerts",
  "text": "✅ Daily market data ingestion completed successfully",
  "attachments": [
    {
      "color": "good",
      "fields": [
        {
          "title": "Symbols Processed",
          "value": "{{ $node['Job Status'].json['result']['symbols_processed'] }}",
          "short": true
        },
        {
          "title": "Data Points",
          "value": "{{ $node['Job Status'].json['result']['total_points_written'] }}",
          "short": true
        }
      ]
    }
  ]
}
```

### Error Notification
```javascript
{
  "channel": "#trading-alerts",
  "text": "❌ Daily market data ingestion failed",
  "attachments": [
    {
      "color": "danger",
      "fields": [
        {
          "title": "Error",
          "value": "{{ $node['Daily Ingest'].json['error'] }}",
          "short": false
        }
      ]
    }
  ]
}
```

## Security Notes

1. **Service Account Key**: n8n の Credentials として安全に保存
2. **Secret Rotation**: 定期的にサービスアカウントキーを更新
3. **Principle of Least Privilege**: 必要最小限の権限のみ付与済み
4. **Monitoring**: Cloud Logging でAPI呼び出しを監視可能