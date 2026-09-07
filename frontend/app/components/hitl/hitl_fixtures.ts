/**
 * Lienmark HITL Clarification Fixtures
 * Realistic production clarification requests matching the 'Shadows Over Broadway' v7 -> v8 revision.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import { UserRole } from '@/lib/types';
import { ClarificationRequestUI, ClarificationStatus, QuestionCategory } from './hitl_types';

export const GOLDEN_CLARIFICATION_REQUESTS: ReadonlyArray<ClarificationRequestUI> = [
  {
    id: 'clarif_poster_noir_detective',
    claimKey: 'poster_noir_detective_magazine',
    scene: 'SC 42 (00:41:12)',
    timecode: '00:41:12',
    assetType: 'artwork',
    assetName: 'Noir Detective Magazine Poster',
    category: QuestionCategory.CHAIN_OF_TITLE,
    assignedRole: UserRole.REVIEWER,
    scriptExcerpt:
      'SCENE 42 - DETECTIVE\'S OFFICE - NIGHT\nJack slams the drawer shut. Behind him on the wall, the framed vintage cover of "Noir Detective Magazine" (April 1948 issue) catches the streetlamp light - the stylized illustration of the masked femme fatale is clearly legible in focus for 8 seconds.',
    rationale:
      'The asset was upgraded from out-of-focus background dressing in Cut v7 to a prominent 8-second foreground hero focus in Cut v8. Without an executed artist clearance or public domain title chain, this represents an actionable copyright infringement exposure under Section 106.',
    questionText:
      'Did art department secure a signed assignment or license from the original illustrator, or was the cover art generated in-house as work-for-hire?',
    suggestedOptions: [
      'Executed artist release on file (work-for-hire)',
      'Original 1948 magazine confirmed public domain',
      'Prop replaced with clearance-cleared substitute asset',
      'Incidental de minimis fair use defense',
    ],
    status: ClarificationStatus.WAITING_FOR_INFO,
    priority: 'urgent',
    createdAt: '2026-09-03T14:35:00.000Z',
    requiredDocumentTypes: ['.pdf', '.docx'],
  },
  {
    id: 'clarif_music_cue_midnight_serenade',
    claimKey: 'music_cue_midnight_serenade',
    scene: 'SC 18 (00:19:40)',
    timecode: '00:19:40',
    assetType: 'music',
    assetName: 'Midnight Serenade Cue',
    category: QuestionCategory.MUSIC_RIGHTS,
    assignedRole: UserRole.PRODUCER,
    scriptExcerpt:
      'SCENE 18 - SPEAKEASY LOUNGE - NIGHT\nThe smoky spotlight swings onto the bandstand. The trumpet player steps up, playing the opening 14 measures of "Midnight Serenade" with full brass accompaniment as Jack enters the crowded room.',
    rationale:
      'Cut v8 introduces a featured, diegetic 28-second performance of the copyrighted composition with foreground dialogue overlapping. E&O underwriter policy requires verifiable synchronization and master recording licenses prior to final cut lock.',
    questionText:
      'Has production acquired the synchronization license and master recording release for the live speakeasy performance of "Midnight Serenade"?',
    suggestedOptions: [
      'Sync and master license fully executed',
      'Direct license with publishing society in progress',
      'Public domain arrangement substituted',
      'Counsel exception schedule requested',
    ],
    status: ClarificationStatus.WAITING_FOR_INFO,
    priority: 'high',
    createdAt: '2026-09-03T14:36:00.000Z',
    requiredDocumentTypes: ['.pdf', '.docx'],
  },
];

export function getClarificationByClaimKey(
  claimKey: string
): ClarificationRequestUI | undefined {
  return GOLDEN_CLARIFICATION_REQUESTS.find(
    (req) => req.claimKey === claimKey || req.claimKey.includes(claimKey)
  );
}
