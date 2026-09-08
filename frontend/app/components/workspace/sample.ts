import type { WorkspaceClaim } from './model';

// Public, illustrative content. Never used to fill a failed authenticated request.
export const sampleClaims: WorkspaceClaim[] = [
  {
    id: 'sample_music_18', title: 'Midnight Serenade', category: 'Music', scene: 'Scene 18',
    status: 'reopened', reason: 'The music cue now appears in the promotional trailer.',
    nextAction: 'Confirm promotional use with a supplemental license.', owner: 'Production team',
    before: 'Feature-film use only', after: 'Feature film + promotional trailer',
  },
  {
    id: 'sample_artwork_42', title: 'Detective magazine cover', category: 'Artwork', scene: 'Scene 42',
    status: 'reopened', reason: 'Background set dressing becomes a featured close-up.',
    nextAction: 'Review the changed prominence and supporting permission.', owner: 'Reviewer',
    before: 'Incidental background appearance', after: 'Featured close-up',
  },
  {
    id: 'sample_footage_31', title: 'City skyline footage', category: 'Footage', scene: 'Scene 31',
    status: 'exception', reason: 'The supplied permission does not establish the requested territory.',
    nextAction: 'Request evidence covering the intended distribution.', owner: 'Production team',
    before: 'US distribution', after: 'Worldwide distribution',
  },
  {
    id: 'sample_artwork_12', title: 'Gallery wall photograph', category: 'Artwork', scene: 'Scene 12',
    status: 'preserved', reason: 'The use and its recorded approval dependencies are unchanged.',
    nextAction: 'No additional investigation in this example.', owner: 'Reviewer',
    before: 'Licensed set dressing', after: 'Unchanged',
  },
  {
    id: 'sample_brand_09', title: 'Café exterior signage', category: 'Brand', scene: 'Scene 09',
    status: 'preserved', reason: 'Scene context and the applicable permission are unchanged.',
    nextAction: 'Carry the sample review lineage forward.', owner: 'Reviewer',
    before: 'Exterior establishing shot', after: 'Unchanged',
  },
  {
    id: 'sample_music_05', title: 'Original opening theme', category: 'Music', scene: 'Scene 05',
    status: 'preserved', reason: 'The composition, recording, and intended use remain unchanged.',
    nextAction: 'No additional investigation in this example.', owner: 'Reviewer',
    before: 'Original commissioned score', after: 'Unchanged',
  },
];
