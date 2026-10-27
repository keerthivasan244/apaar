import nacl from "tweetnacl";
import type { CredentialPayload, PublicKeyInfo } from "../api/types";

const KEY_CACHE = "apaar.publicKey";

export function b64urlToBytes(text: string): Uint8Array {
  const b64 = text.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (text.length % 4)) % 4);
  const bin = atob(b64);
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

export function b64ToBytes(text: string): Uint8Array {
  return Uint8Array.from(atob(text), (c) => c.charCodeAt(0));
}

export function cachedKey(): PublicKeyInfo | null {
  try {
    const raw = localStorage.getItem(KEY_CACHE);
    return raw ? (JSON.parse(raw) as PublicKeyInfo) : null;
  } catch {
    return null;
  }
}

export function cacheKey(key: PublicKeyInfo) {
  try {
    localStorage.setItem(KEY_CACHE, JSON.stringify(key));
  } catch {
    /* storage unavailable */
  }
}

export interface VerifyOutcome {
  valid: boolean;
  payload: CredentialPayload | null;
  reason?: string;
}

/** Verify a credential token entirely in the browser (no network). */
export function verifyToken(token: string, key: PublicKeyInfo): VerifyOutcome {
  const parts = token.trim().split(".");
  if (parts.length !== 2) return { valid: false, payload: null, reason: "Token must have two parts separated by a dot" };
  const [payloadB64, sigB64] = parts;
  try {
    const sig = b64urlToBytes(sigB64);
    const pub = b64ToBytes(key.public_key_b64);
    if (sig.length !== nacl.sign.signatureLength) return { valid: false, payload: null, reason: "Signature has the wrong length" };
    const ok = nacl.sign.detached.verify(new TextEncoder().encode(payloadB64), sig, pub);
    if (!ok) return { valid: false, payload: null, reason: "Signature does not match the published key" };
    const payload = JSON.parse(new TextDecoder().decode(b64urlToBytes(payloadB64))) as CredentialPayload;
    if (payload.kid !== key.kid) return { valid: false, payload: null, reason: `Signed with unknown key ${payload.kid}` };
    return { valid: true, payload };
  } catch {
    return { valid: false, payload: null, reason: "Token is malformed" };
  }
}

export function tokenFromInput(input: string): string {
  const v = input.trim();
  try {
    const url = new URL(v);
    return url.searchParams.get("token") || v;
  } catch {
    return v;
  }
}
