/**
 * frontend/tests/research.test.ts
 * Automated unit test suite for Sprint 3.1 clearance research UI utilities and contracts.
 * Enforces file <= 250 lines and function <= 40 lines strictly.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DomainAuthorityTier,
  QueryTokenType,
} from '../app/components/research/types';
import {
  formatLatency,
  getLatencyBadgeColor,
  getAuthorityBadgeStyle,
  classifyDomainAuthority,
  extractDomain,
  sanitizeUrl,
  tokenizeQueryString,
  getHttpStatusBadgeStyle,
} from '../app/components/research/research_utils';

test('formatLatency: handles sub-second, multi-second, zero, and invalid values', () => {
  assert.equal(formatLatency(120), '120 ms');
  assert.equal(formatLatency(45.4), '45 ms');
  assert.equal(formatLatency(1500), '1.50 s');
  assert.equal(formatLatency(2340), '2.34 s');
  assert.equal(formatLatency(0), '0 ms');
  assert.equal(formatLatency(-50), '0 ms');
  assert.equal(formatLatency(NaN), '0 ms');
});

test('getLatencyBadgeColor: returns correct styling thresholds', () => {
  const optimal = getLatencyBadgeColor(150);
  assert.equal(optimal.label, 'Optimal');
  assert.ok(optimal.text.includes('emerald'));

  const moderate = getLatencyBadgeColor(450);
  assert.equal(moderate.label, 'Moderate');
  assert.ok(moderate.text.includes('amber'));

  const high = getLatencyBadgeColor(1200);
  assert.equal(high.label, 'High Latency');
  assert.ok(high.text.includes('rose'));
});

test('getAuthorityBadgeStyle: validates styling palette for all 3 tiers', () => {
  const tier1 = getAuthorityBadgeStyle(DomainAuthorityTier.TIER_1_GOVERNMENT);
  assert.equal(tier1.iconName, 'ShieldCheck');
  assert.ok(tier1.text.includes('amber'));

  const tier2 = getAuthorityBadgeStyle(DomainAuthorityTier.TIER_2_RIGHTS_ORG);
  assert.equal(tier2.iconName, 'Building2');
  assert.ok(tier2.text.includes('sky'));

  const tier3 = getAuthorityBadgeStyle(DomainAuthorityTier.TIER_3_WEB);
  assert.equal(tier3.iconName, 'Globe');
  assert.ok(tier3.text.includes('slate'));

  // Fallback for invalid tier
  const fallback = getAuthorityBadgeStyle('unknown_tier');
  assert.equal(fallback.tier, DomainAuthorityTier.TIER_3_WEB);
});

test('classifyDomainAuthority: correctly categorizes registries, rights orgs, and web', () => {
  // Tier 1 Government Registries
  assert.equal(classifyDomainAuthority('https://tmsearch.uspto.gov/search'), DomainAuthorityTier.TIER_1_GOVERNMENT);
  assert.equal(classifyDomainAuthority('https://publicrecords.copyright.gov'), DomainAuthorityTier.TIER_1_GOVERNMENT);
  assert.equal(classifyDomainAuthority('https://www.wipo.int/branddb/en/'), DomainAuthorityTier.TIER_1_GOVERNMENT);
  assert.equal(classifyDomainAuthority('https://loc.gov/item/1234'), DomainAuthorityTier.TIER_1_GOVERNMENT);
  assert.equal(classifyDomainAuthority('uspto.report/company/Example'), DomainAuthorityTier.TIER_1_GOVERNMENT);

  // Tier 2 Rights Organizations
  assert.equal(classifyDomainAuthority('https://www.ascap.com/repertory'), DomainAuthorityTier.TIER_2_RIGHTS_ORG);
  assert.equal(classifyDomainAuthority('https://repertoire.bmi.com'), DomainAuthorityTier.TIER_2_RIGHTS_ORG);
  assert.equal(classifyDomainAuthority('https://www.sesac.com/repertory'), DomainAuthorityTier.TIER_2_RIGHTS_ORG);
  assert.equal(classifyDomainAuthority('https://songview.com/search'), DomainAuthorityTier.TIER_2_RIGHTS_ORG);
  assert.equal(classifyDomainAuthority('https://www.harryfox.com'), DomainAuthorityTier.TIER_2_RIGHTS_ORG);

  // Tier 3 Public Web Sources
  assert.equal(classifyDomainAuthority('https://en.wikipedia.org/wiki/Song'), DomainAuthorityTier.TIER_3_WEB);
  assert.equal(classifyDomainAuthority('https://www.discogs.com/release/123'), DomainAuthorityTier.TIER_3_WEB);
  assert.equal(classifyDomainAuthority('https://pitchfork.com/reviews'), DomainAuthorityTier.TIER_3_WEB);
});

test('extractDomain: handles protocols, subdomains, ports, and edge cases', () => {
  assert.equal(extractDomain('https://tmsearch.uspto.gov/bin/gate.exe'), 'tmsearch.uspto.gov');
  assert.equal(extractDomain('http://www.ascap.com/ace/'), 'ascap.com');
  assert.equal(extractDomain('copyright.gov/records'), 'copyright.gov');
  assert.equal(extractDomain('https://sub.domain.org:8080/path'), 'sub.domain.org');
  assert.equal(extractDomain(''), '');
  assert.equal(extractDomain('   '), '');
});

test('sanitizeUrl: allows valid HTTP/HTTPS and rejects malicious protocols', () => {
  assert.equal(
    sanitizeUrl('https://tmsearch.uspto.gov/case/123'),
    'https://tmsearch.uspto.gov/case/123'
  );
  assert.equal(sanitizeUrl('http://ascap.com'), 'http://ascap.com/');

  // XSS & dangerous protocols must return null
  assert.equal(sanitizeUrl('javascript:alert(1)'), null);
  assert.equal(sanitizeUrl('data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg=='), null);
  assert.equal(sanitizeUrl('vbscript:msgbox(1)'), null);
  assert.equal(sanitizeUrl('file:///etc/passwd'), null);
  assert.equal(sanitizeUrl(''), null);
  assert.equal(sanitizeUrl('https://example.com/\x00bad'), null);
});

test('tokenizeQueryString: correctly parses search operators and keywords', () => {
  const query = 'site:ascap.com "Hold On" -lyrics -chords Alabama Shakes OR BMI';
  const tokens = tokenizeQueryString(query);

  const siteToken = tokens.find((t) => t.type === QueryTokenType.SITE);
  assert.ok(siteToken);
  assert.equal(siteToken?.value, 'site:ascap.com');

  const quoteToken = tokens.find((t) => t.type === QueryTokenType.QUOTE);
  assert.ok(quoteToken);
  assert.equal(quoteToken?.value, 'Hold On');

  const negTokens = tokens.filter((t) => t.type === QueryTokenType.NEGATIVE);
  assert.equal(negTokens.length, 2);
  assert.equal(negTokens[0].value, '-lyrics');
  assert.equal(negTokens[1].value, '-chords');

  const opToken = tokens.find((t) => t.type === QueryTokenType.OPERATOR);
  assert.ok(opToken);
  assert.equal(opToken?.value, 'OR');

  const terms = tokens.filter((t) => t.type === QueryTokenType.TERM);
  assert.ok(terms.some((t) => t.value === 'Alabama'));
  assert.ok(terms.some((t) => t.value === 'Shakes'));
});

test('getHttpStatusBadgeStyle: categorizes HTTP status codes properly', () => {
  assert.equal(getHttpStatusBadgeStyle(200).label, '200 OK');
  assert.ok(getHttpStatusBadgeStyle(200).text.includes('emerald'));

  assert.equal(getHttpStatusBadgeStyle(301).label, '301 Redirect');
  assert.ok(getHttpStatusBadgeStyle(301).text.includes('sky'));

  assert.equal(getHttpStatusBadgeStyle(404).label, '404 Client Error');
  assert.ok(getHttpStatusBadgeStyle(404).text.includes('amber'));

  assert.equal(getHttpStatusBadgeStyle(502).label, '502 Server Error');
  assert.ok(getHttpStatusBadgeStyle(502).text.includes('rose'));
});
