## ADDED Requirements

### Requirement: Delete ticker blocked when active positions exist
The system SHALL check the orders/positions table before deleting a watchlist ticker. If any active order or position exists for that ticker, the DELETE request MUST be rejected with HTTP 400.

#### Scenario: Delete ticker with active position
- **WHEN** user attempts to DELETE /settings/watchlist/AAPL and AAPL has an active option position
- **THEN** system returns HTTP 400 with message "无法移除该标的！当前仍持有其活跃仓位，请先平仓以防止产生孤儿订单。"

#### Scenario: Delete ticker with no active positions
- **WHEN** user attempts to DELETE /settings/watchlist/TSLA and TSLA has no active orders or positions
- **THEN** system proceeds with normal deletion and returns HTTP 200

#### Scenario: Delete ticker with only closed/cancelled positions
- **WHEN** user attempts to DELETE /settings/watchlist/AMD and AMD only has positions with status "closed" or "cancelled"
- **THEN** system proceeds with normal deletion (closed positions are not active)
