/**
 * Lienmark Directive Shortcuts & Citation Templates (Sprint 5.2)
 * Provides static template libraries for clearance counsel review and directives.
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import { CitationTemplateUI, DirectiveShortcut } from './review_types';

export const DIRECTIVE_SHORTCUTS: ReadonlyArray<DirectiveShortcut> = [
  {
    id: 'master_recording_owner',
    label: 'Master Recording Owner',
    text: 'Check master recording owner',
    category: 'Music Rights',
  },
  {
    id: 'foreign_distribution_holdback',
    label: 'Foreign Holdback',
    text: 'Verify foreign distribution holdback',
    category: 'Distribution',
  },
  {
    id: 'ascap_1972_live',
    label: 'ASCAP 1972 Live Adaptation',
    text: 'Re-search ASCAP for 1972 live adaptation',
    category: 'Music Rights',
  },
  {
    id: 'fair_use_transformative',
    label: 'Fair Use 4-Factor',
    text: 'Confirm transformative use and market substitution under Campbell v. Acuff-Rose',
    category: 'Copyright',
  },
  {
    id: 'trademark_de_minimis',
    label: 'Trademark De Minimis',
    text: 'Investigate incidental background focal exposure duration under 15 U.S.C. § 1125',
    category: 'Trademark',
  },
  {
    id: 'public_domain_pre_1929',
    label: 'Pre-1929 Public Domain',
    text: 'Verify pre-1929 initial publication date and absence of renewed derivative claims',
    category: 'Public Domain',
  },
];

export const DEFAULT_CITATION_TEMPLATES: ReadonlyArray<CitationTemplateUI> = [
  {
    id: 'fair_use_107',
    category: 'Copyright',
    title: 'Fair Use Defense (17 U.S.C. § 107)',
    statute: '17 U.S.C. § 107',
    text: '17 U.S.C. § 107 Fair Use: Evaluated under four statutory factors: (1) purpose and character of use is transformative commentary; (2) nature of copyrighted work; (3) substantiality of portion used in relation to whole is strictly fleeting; (4) zero negative effect upon the potential market for original work.',
  },
  {
    id: 'sync_master_clause_4a',
    category: 'Music Rights',
    title: 'Sync & Master License (Clause 4(a))',
    statute: 'Standard Sync/Master Form Cl. 4(a)',
    text: 'Clause 4(a) Audiovisual Synchronization: Grantor confirms irrevocable, worldwide synchronization and master recording exploitation rights in all media now known or hereafter devised, in perpetuity, with warranties of non-infringement fully executed.',
  },
  {
    id: 'lanham_act_43a',
    category: 'Trademark',
    title: 'Lanham Act De Minimis (15 U.S.C. § 1125)',
    statute: '15 U.S.C. § 1125(a)',
    text: '15 U.S.C. § 1125(a): Incidental and out-of-focus background placement creates no likelihood of consumer confusion, false endorsement, or trademark tarnishment pursuant to Second Circuit Rogers v. Grimaldi standard.',
  },
  {
    id: 'public_domain_304',
    category: 'Public Domain',
    title: 'Public Domain Status (17 U.S.C. § 304)',
    statute: '17 U.S.C. § 304 / Sonny Bono CTEA',
    text: '17 U.S.C. § 304: Work published prior to January 1, 1929 has permanently entered the United States public domain; unrestricted exploitation permitted without statutory royalties or license requirements.',
  },
  {
    id: 'incidental_ephemeral_112',
    category: 'General Clearance',
    title: 'Ephemeral Reproduction (17 U.S.C. § 112)',
    statute: '17 U.S.C. § 112',
    text: '17 U.S.C. § 112: Transient reproduction solely for technical broadcast assembly and non-standalone display qualifies for statutory exemption from direct copyright liability.',
  },
];
