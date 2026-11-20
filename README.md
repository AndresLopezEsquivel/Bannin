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
