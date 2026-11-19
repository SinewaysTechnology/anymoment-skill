import { createHmac, timingSafeEqual } from 'node:crypto';

export type SignatureCheck = {
	ok: boolean;
	reason: string;
};

export function hmacSha256Hex(secret: string, message: string): string {
	return createHmac('sha256', secret).update(message).digest('hex');
}

function safeEqualHex(left: string, right: string): boolean {
	const leftBuffer = Buffer.from(left, 'utf8');
	const rightBuffer = Buffer.from(right, 'utf8');
	if (leftBuffer.length !== rightBuffer.length) return false;
	return timingSafeEqual(leftBuffer, rightBuffer);
}

/**
 * AnyMoment signs timestamp + "." + rawBody with HMAC-SHA256 and sends the hex digest
 * in X-AnyMoment-Signature. Compare against the raw bytes. Re-encoding the JSON will not match.
 */
export function verifyAnyMomentSignature(options: {
	secret: string;
	timestamp: string;
	rawBody: string;
	signature: string;
	toleranceSeconds: number;
	nowSeconds?: number;
}): SignatureCheck {
	const secret = options.secret.trim();
	const timestamp = options.timestamp.trim();
	const signature = options.signature.trim().toLowerCase();
	if (!secret) {
		return {
			ok: false,
			reason:
				'No signing secret is available. Set Webhook Signing Secret on the AnyMoment API credential, or activate the trigger so a generated secret can be stored.',
		};
	}
	if (!timestamp || !signature) {
		return {
			ok: false,
			reason: 'X-AnyMoment-Timestamp or X-AnyMoment-Signature is missing.',
		};
	}
	if (!/^[0-9a-f]+$/.test(signature) || signature.length % 2 !== 0) {
		return { ok: false, reason: 'X-AnyMoment-Signature is not hex.' };
	}
	const timestampNumber = Number(timestamp);
	if (!Number.isFinite(timestampNumber)) {
		return { ok: false, reason: 'X-AnyMoment-Timestamp is not a number.' };
	}
	if (options.toleranceSeconds > 0) {
		const now = options.nowSeconds ?? Date.now() / 1000;
		if (Math.abs(now - timestampNumber) > options.toleranceSeconds) {
			return {
				ok: false,
				reason: 'X-AnyMoment-Timestamp is outside the allowed window.',
			};
		}
	}
	const expected = hmacSha256Hex(secret, `${timestamp}.${options.rawBody}`);
	if (!safeEqualHex(expected, signature)) {
		return { ok: false, reason: 'Signature does not match the raw body.' };
	}
	return { ok: true, reason: 'ok' };
}
