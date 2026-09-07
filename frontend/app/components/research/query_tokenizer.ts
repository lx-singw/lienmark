/**
 * query_tokenizer.ts
 * Query string tokenizer and syntax parser for clearance research UI.
 * Extracts site: filters, negative exclusions, exact quotes, and logical operators.
 * Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import { QueryTokenType, type QueryToken } from './types';

// Regex matching search syntax operators and terms in clearance queries
const QUERY_TOKEN_REGEX =
  /"([^"]*)"|(site:[^\s]+)|(-[^\s]+)|\b(OR|AND|NOT)\b|([^\s]+)/gi;

/**
 * Tokenizes a raw search query into typed syntax elements.
 * Returns an array of QueryTokens representing sites, negatives, quotes, operators, and terms.
 */
export function tokenizeQueryString(
  query: string
): ReadonlyArray<QueryToken> {
  if (!query || typeof query !== 'string') return [];
  const trimmed = query.trim();
  if (!trimmed) return [];

  const tokens: QueryToken[] = [];
  let match: RegExpExecArray | null;

  // Reset regex state for fresh iteration
  QUERY_TOKEN_REGEX.lastIndex = 0;

  while ((match = QUERY_TOKEN_REGEX.exec(trimmed)) !== null) {
    const [raw, quoteVal, siteVal, negVal, opVal, termVal] = match;
    if (siteVal) {
      tokens.push({ type: QueryTokenType.SITE, value: siteVal, raw });
    } else if (negVal) {
      tokens.push({ type: QueryTokenType.NEGATIVE, value: negVal, raw });
    } else if (quoteVal !== undefined) {
      tokens.push({ type: QueryTokenType.QUOTE, value: quoteVal, raw });
    } else if (opVal) {
      tokens.push({ type: QueryTokenType.OPERATOR, value: opVal, raw });
    } else if (termVal) {
      tokens.push({ type: QueryTokenType.TERM, value: termVal, raw });
    }
  }

  return tokens;
}
