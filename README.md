# Bannin

**Bannin is a work in progress.** It is being built as a real-time fraud-detection system that aims to determine whether an online card payment should be approved, reviewed, or declined before the merchant submits it for bank authorization.

## The Problem

Online card fraud is costly for merchants. When a legitimate cardholder disputes a fraudulent charge, the merchant typically loses the goods or services provided, the payment, and an additional chargeback fee. But blocking transactions too aggressively has a cost as well: every legitimate customer turned away represents a lost sale and potentially a lost customer. Merchants therefore need to stop fraud without turning away genuine customers.

Bannin focuses on card-not-present (CNP) fraud, a type of card fraud in which the physical card is not required to complete a transaction. It is common in online payments and occurs when a fraudster obtains a cardholder's payment information through various means, such as data breaches or phishing, and uses it to make unauthorized purchases.

CNP fraud is particularly challenging to detect because the physical card is absent and fraud techniques continuously evolve. Detection must happen within milliseconds, while the customer is checking out, using indirect signals such as the device, email address, IP address, and past behavior to determine whether a transaction is legitimate.

## Where Bannin Fits

Bannin is being built as a standalone service that the merchant's backend calls during checkout. When a customer places an order, the merchant's app sends it to the merchant's backend, which calls Bannin with the payment details and supporting signals such as the device, IP address, and email address. Bannin returns an approve, review, or decline decision. If the payment is approved or sent to review, the merchant's backend submits it to its payment processor, which routes the transaction to the cardholder's issuing bank for authorization.

The fraud-screening result Bannin provides is a preliminary risk assessment, not the bank's authorization decision. The issuer makes the final authorization decision based on its own checks, which may include available funds or credit, and card status.

Some large merchants build their own fraud-detection service in-house; others call a third-party API such as [Sift](https://sift.com/) or [Signifyd](https://www.signifyd.com/); and payment processors such as Stripe integrate fraud detection directly into their payment flow through products like [Stripe Radar](https://stripe.com/radar), so the merchant never calls a separate service. Bannin follows the in-house model, serving a single merchant, but exposes an API similar to that of a third-party service, allowing the merchant's backend to call it over the network like any other service.

### Application Request Flow

Currently, a payment request sent by the merchant's backend to `POST /score` passes through six stages in Bannin's application: API key authentication, request body checks, request validation, feature building, scoring, and decision-making. These stages form the foundation of the application's request-processing flow, but they will continue to evolve as development progresses.

#### 1. API Key Authentication

The application requires every request to include an API key in the `Authorization` header using the `Bearer` authentication scheme. This check is implemented in `src/bannin/auth.py`.

If the header is missing or doesn't use the `Bearer` scheme, the application responds with HTTP `401 Unauthorized` and the error code `api_key_missing`. If the provided key doesn't match any of the stored keys, it responds with the same status code and the error code `api_key_invalid`.

The keys are loaded once, when the application starts. When deployed on AWS, they're stored as `SecureString` parameters in AWS Systems Manager Parameter Store; locally, they're read from the `BANNIN_API_KEYS` environment variable. Up to two keys are valid at once, so a key can be replaced without downtime.

#### 2. Request Body Checks

Before validating the request's fields, the application performs two checks on the request body.

**Size check:** The application enforces a maximum request body size of 64 KiB. If the declared `Content-Length` exceeds this limit, the request is rejected immediately with HTTP `413 Content Too Large` and the error code `body_too_large`, without reading the body. Otherwise, the application counts the bytes as they arrive and rejects the request as soon as the limit is exceeded.

**JSON format check:** A body that isn't valid JSON, or is valid JSON but not an object (such as an array, string, number, or `null`), is rejected with HTTP `400 Bad Request` and the error code `body_invalid`.

When deployed on AWS, Caddy, the web server in front of the application, also limits the request body size, but at 1 MiB rather than 64 KiB. It rejects excessively large requests before they reach the application, with an empty `413` response. The application's stricter 64 KiB limit is tailored to the expected size of scoring requests.

#### 3. Request Validation

Bannin's API contract is defined in `api/openapi.yaml`, while request validation is implemented in `src/bannin/validation.py`. The validator checks required fields first, followed by optional fields.

**Required fields:** Every request must include `payment_id`, `amount`, `currency`, and `card_id`. These fields are validated in that order. If a field is missing or contains an invalid value, validation stops at the first failure and the application responds with HTTP `400 Bad Request`. The error code is either `parameter_missing` or `parameter_invalid`, and the response identifies the field that caused the error.

**Optional fields:** Additional information, such as email addresses, IP addresses, and billing or shipping addresses, can be included to provide more context for fraud detection. Invalid or unrecognized optional fields don't cause the request to fail. Instead, they're added to the `ignored_fields` list in the response and marked as either `invalid` or `unrecognized`, depending on the reason they were ignored. Only the field name and reason are included; the original value is never returned.

Once a request passes validation, its fraud risk is assessed in three stages: feature building, scoring, and decision-making.

#### 4. Feature Building

`src/bannin/features.py` currently returns an empty dictionary (`{}`) on every call. As development progresses, this stage will compute the features used as input to the machine-learning model.

#### 5. Scoring

The scorer in `src/bannin/scorer.py` is currently a placeholder that returns a fixed score of `12.37` on every call, without reading or using any features. It will eventually be replaced by a machine-learning model that consumes the computed features and produces a fraud score.

#### 6. Decision-Making

Decision-making currently uses a simple threshold-based approach, implemented in `src/bannin/decision.py`. The thresholds are defined in `config/thresholds.toml` and determine whether a transaction should be approved, sent for review, or declined. They're read once, when the application starts, so changing them requires a restart and a new `version` in the file. This approach is a starting point and will evolve as development progresses.

The current thresholds are:

| Fraud score | Decision |
|---|---|
| 85 or above | Decline |
| 60 to below 85 | Review |
| Below 60 | Approve |

Since the current scorer always returns `12.37`, all validated transactions that reach this stage are currently approved.

#### Response Format

For a valid request, `POST /score` returns HTTP `200 OK` with the fraud assessment. Requests that are rejected return an error response with the appropriate HTTP status code and a standardized error object.

**Successful response:** A valid request such as:

```json
{
  "payment_id": "pay_1",
  "amount": 1000,
  "currency": "USD",
  "card_id": "card_1",
  "colour": "blue"
}
```

returns HTTP `200 OK` with the following response:

```json
{
  "payment_id": "pay_1",
  "decision": "approve",
  "score": 12.37,
  "reasons": [],
  "ignored_fields": [
    {
      "field": "colour",
      "code": "unrecognized",
      "message": "is not a field Bannin uses"
    }
  ]
}
```

The decision is currently always `approve` and the score is always `12.37`, reflecting the placeholder scorer. The `reasons` list remains empty until the scoring model is implemented. The `ignored_fields` list is empty when all provided fields are recognized and valid.

**Error response:** Rejected requests return HTTP `400`, `401`, `413`, or `500`, depending on the cause. All error responses from `POST /score` follow the same structure, implemented in `src/bannin/errors.py`:

```json
{
  "error": {
    "type": "invalid_request",
    "code": "parameter_missing",
    "message": "amount is required.",
    "field": "amount"
  }
}
```

The `field` property is included only when the error is associated with a specific field.

The following table summarizes the error types and codes returned by `POST /score`:

| HTTP status | `type` | `code` |
|---|---|---|
| `401 Unauthorized` | `authentication` | `api_key_missing`, `api_key_invalid` (includes `WWW-Authenticate: Bearer` header) |
| `413 Content Too Large` | `invalid_request` | `body_too_large` |
| `400 Bad Request` | `invalid_request` | `body_invalid`, `parameter_missing`, `parameter_invalid` |
| `500 Internal Server Error` | `server_error` | `internal_error` (for unexpected errors; no internal details are returned) |

Unknown paths and unsupported methods return the web framework's default `404` and `405` responses, which don't follow this structure.
