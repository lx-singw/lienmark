/**
 * Lienmark Hollywood Studio Legal Ops - Sound Effects Synthesizer
 *
 * Provides zero-dependency, native Web Audio API acoustic synthesis for
 * statutory clearance actions. No external audio files (.mp3, .wav) required.
 *
 * Audio Specifications:
 * - playStampSound(): Crisp mechanical stamp click (plays only upon verified HTTP 200 re-attestation).
 * - playGavelSound(): Resonant wooden gavel strike (plays only upon verified HTTP 200 exception rejection).
 * - Master mute toggle with localStorage persistence.
 * - Safe for Server-Side Rendering (SSR) in Next.js (safe guards on `typeof window !== 'undefined'`).
 *
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

const STORAGE_MUTE_KEY = 'lienmark_sound_muted';
const MUTE_CHANGE_EVENT = 'lienmark-sound-mute-changed';

let sharedAudioContext: AudioContext | null = null;

/**
 * Lazily obtains or creates the shared Web Audio API context.
 * Returns null in SSR environments or if Web Audio is unsupported.
 */
function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    if (!sharedAudioContext) {
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;

      if (!AudioCtx) {
        return null;
      }
      sharedAudioContext = new AudioCtx();
    }

    // Auto-resume if suspended by browser autoplay policy
    if (sharedAudioContext.state === 'suspended') {
      sharedAudioContext.resume().catch(() => {
        // Silently catch if user has not yet interacted with the page
      });
    }

    return sharedAudioContext;
  } catch (err: unknown) {
    console.warn('[SoundEffects] Unable to initialize Web Audio context:', err);
    return null;
  }
}

/**
 * Checks whether audio sound effects are globally muted.
 * Defaults to false (unmuted). Safe in SSR.
 */
export function isSoundMuted(): boolean {
  if (typeof window === 'undefined') {
    return true; // Default to silent in SSR
  }

  try {
    const stored = window.localStorage.getItem(STORAGE_MUTE_KEY);
    return stored === 'true';
  } catch {
    return false;
  }
}

/**
 * Sets the global master mute state and persists it to localStorage.
 * Dispatches a custom window event to allow UI controls to synchronize.
 */
export function setSoundMuted(muted: boolean): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    window.localStorage.setItem(STORAGE_MUTE_KEY, muted ? 'true' : 'false');
    window.dispatchEvent(
      new CustomEvent(MUTE_CHANGE_EVENT, {
        detail: { muted },
      })
    );
  } catch (err: unknown) {
    console.warn('[SoundEffects] Unable to persist mute state:', err);
  }
}

/**
 * Toggles the master mute state and returns the new state.
 */
export function toggleSoundMuted(): boolean {
  const newState = !isSoundMuted();
  setSoundMuted(newState);
  return newState;
}

/**
 * Subscribes to mute state changes across the application.
 * Returns an unsubscribe callback for clean component unmounting.
 */
export function subscribeToMuteState(listener: (muted: boolean) => void): () => void {
  if (typeof window === 'undefined') {
    return () => {};
  }

  const handler = (event: Event) => {
    const customEvent = event as CustomEvent<{ muted: boolean }>;
    listener(customEvent.detail?.muted ?? isSoundMuted());
  };

  window.addEventListener(MUTE_CHANGE_EVENT, handler);
  return () => {
    window.removeEventListener(MUTE_CHANGE_EVENT, handler);
  };
}

/**
 * Generates an internal audio buffer containing white noise for transient modeling.
 */
function createNoiseBuffer(ctx: AudioContext, durationSec: number): AudioBuffer {
  const sampleRate = ctx.sampleRate;
  const bufferSize = Math.floor(sampleRate * durationSec);
  const buffer = ctx.createBuffer(1, bufferSize, sampleRate);
  const data = buffer.getChannelData(0);

  for (let i = 0; i < bufferSize; i++) {
    data[i] = Math.random() * 2 - 1;
  }

  return buffer;
}

/**
 * Synthesizes a crisp mechanical stamp click.
 * Acoustic profile:
 * 1. High-frequency mechanical spring click / release snap (bandpassed noise + transient sine drop).
 * 2. Solid rubber-die impact thump on heavy bond paper (rapid pitch drop 240Hz -> 65Hz).
 * 3. Secondary micro-spring reset rattle at +42ms.
 *
 * Invoked strictly upon verified HTTP 200 re-attestation determinations.
 */
export function playStampSound(): void {
  if (typeof window === 'undefined' || isSoundMuted()) {
    return;
  }

  const ctx = getAudioContext();
  if (!ctx) return;

  try {
    const now = ctx.currentTime;
    const masterGain = ctx.createGain();
    masterGain.gain.setValueAtTime(0.35, now);
    masterGain.connect(ctx.destination);

    // --- 1. Mechanical Metal Spring Click Transient ---
    const noiseBuffer = createNoiseBuffer(ctx, 0.04);
    const noiseSource = ctx.createBufferSource();
    noiseSource.buffer = noiseBuffer;

    const noiseFilter = ctx.createBiquadFilter();
    noiseFilter.type = 'bandpass';
    noiseFilter.frequency.setValueAtTime(2200, now);
    noiseFilter.Q.setValueAtTime(3.5, now);

    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0.7, now);
    noiseGain.gain.exponentialRampToValueAtTime(0.001, now + 0.035);

    noiseSource.connect(noiseFilter);
    noiseFilter.connect(noiseGain);
    noiseGain.connect(masterGain);
    noiseSource.start(now);
    noiseSource.stop(now + 0.04);

    // High snap chirp
    const snapOsc = ctx.createOscillator();
    const snapGain = ctx.createGain();
    snapOsc.type = 'triangle';
    snapOsc.frequency.setValueAtTime(1400, now);
    snapOsc.frequency.exponentialRampToValueAtTime(380, now + 0.03);

    snapGain.gain.setValueAtTime(0.4, now);
    snapGain.gain.exponentialRampToValueAtTime(0.001, now + 0.03);

    snapOsc.connect(snapGain);
    snapGain.connect(masterGain);
    snapOsc.start(now);
    snapOsc.stop(now + 0.035);

    // --- 2. Solid Rubber Stamp Die Impact Thud ---
    const thudOsc = ctx.createOscillator();
    const thudGain = ctx.createGain();
    thudOsc.type = 'sine';
    thudOsc.frequency.setValueAtTime(240, now);
    thudOsc.frequency.exponentialRampToValueAtTime(65, now + 0.08);

    thudGain.gain.setValueAtTime(0.8, now);
    thudGain.gain.exponentialRampToValueAtTime(0.001, now + 0.085);

    thudOsc.connect(thudGain);
    thudGain.connect(masterGain);
    thudOsc.start(now);
    thudOsc.stop(now + 0.09);

    // --- 3. Secondary Micro-Spring Reset Latch (+42ms) ---
    const resetTime = now + 0.042;
    const resetNoise = ctx.createBufferSource();
    resetNoise.buffer = createNoiseBuffer(ctx, 0.025);

    const resetFilter = ctx.createBiquadFilter();
    resetFilter.type = 'bandpass';
    resetFilter.frequency.setValueAtTime(3200, resetTime);
    resetFilter.Q.setValueAtTime(4.0, resetTime);

    const resetGain = ctx.createGain();
    resetGain.gain.setValueAtTime(0.3, resetTime);
    resetGain.gain.exponentialRampToValueAtTime(0.001, resetTime + 0.022);

    resetNoise.connect(resetFilter);
    resetFilter.connect(resetGain);
    resetGain.connect(masterGain);
    resetNoise.start(resetTime);
    resetNoise.stop(resetTime + 0.025);
  } catch (err: unknown) {
    console.warn('[SoundEffects] playStampSound synthesis failed:', err);
  }
}

/**
 * Synthesizes a resonant wooden gavel strike.
 * Acoustic profile:
 * 1. Immediate high-density hardwood impact transient (shaped impulse crack).
 * 2. Deep solid hardwood fundamental resonance at 320Hz sliding down to 175Hz.
 * 3. Warm judicial soundblock harmonic overtones at 520Hz, 840Hz, and 1260Hz decaying over 320ms.
 *
 * Invoked strictly upon verified HTTP 200 exception rejection determinations.
 */
export function playGavelSound(): void {
  if (typeof window === 'undefined' || isSoundMuted()) {
    return;
  }

  const ctx = getAudioContext();
  if (!ctx) return;

  try {
    const now = ctx.currentTime;
    const masterGain = ctx.createGain();
    masterGain.gain.setValueAtTime(0.38, now);
    masterGain.connect(ctx.destination);

    // --- 1. Hardwood Initial Strike Impulse ---
    const impulseBuffer = createNoiseBuffer(ctx, 0.02);
    const impulseSource = ctx.createBufferSource();
    impulseSource.buffer = impulseBuffer;

    const impulseFilter = ctx.createBiquadFilter();
    impulseFilter.type = 'bandpass';
    impulseFilter.frequency.setValueAtTime(800, now);
    impulseFilter.Q.setValueAtTime(2.0, now);

    const impulseGain = ctx.createGain();
    impulseGain.gain.setValueAtTime(0.8, now);
    impulseGain.gain.exponentialRampToValueAtTime(0.001, now + 0.018);

    impulseSource.connect(impulseFilter);
    impulseFilter.connect(impulseGain);
    impulseGain.connect(masterGain);
    impulseSource.start(now);
    impulseSource.stop(now + 0.02);

    // --- 2. Dense Wooden Gavel Head Fundamental Body ---
    const fundamentalOsc = ctx.createOscillator();
    const fundamentalGain = ctx.createGain();
    fundamentalOsc.type = 'triangle';
    fundamentalOsc.frequency.setValueAtTime(320, now);
    fundamentalOsc.frequency.exponentialRampToValueAtTime(175, now + 0.28);

    fundamentalGain.gain.setValueAtTime(0.9, now);
    fundamentalGain.gain.exponentialRampToValueAtTime(0.001, now + 0.32);

    fundamentalOsc.connect(fundamentalGain);
    fundamentalGain.connect(masterGain);
    fundamentalOsc.start(now);
    fundamentalOsc.stop(now + 0.33);

    // --- 3. Sound Block Acoustic Resonant Overtones (Wood Harmonics) ---
    const harmonics = [
      { freq: 520, gain: 0.45, decay: 0.22 },
      { freq: 840, gain: 0.25, decay: 0.16 },
      { freq: 1260, gain: 0.15, decay: 0.11 },
    ];

    harmonics.forEach(({ freq, gain, decay }) => {
      const harmOsc = ctx.createOscillator();
      const harmGain = ctx.createGain();
      harmOsc.type = 'sine';
      harmOsc.frequency.setValueAtTime(freq, now);
      harmOsc.frequency.exponentialRampToValueAtTime(freq * 0.88, now + decay);

      harmGain.gain.setValueAtTime(gain, now);
      harmGain.gain.exponentialRampToValueAtTime(0.001, now + decay);

      harmOsc.connect(harmGain);
      harmGain.connect(masterGain);
      harmOsc.start(now);
      harmOsc.stop(now + decay + 0.01);
    });
  } catch (err: unknown) {
    console.warn('[SoundEffects] playGavelSound synthesis failed:', err);
  }
}

/**
 * Defensive verification wrapper: plays mechanical stamp click ONLY if HTTP status is 200.
 */
export function playVerifiedAttestationSound(httpStatus = 200): void {
  if (httpStatus === 200) {
    playStampSound();
  } else {
    console.warn(
      `[SoundEffects] Attestation sound suppressed: HTTP status ${httpStatus} is not 200 OK.`
    );
  }
}

/**
 * Defensive verification wrapper: plays wooden gavel strike ONLY if HTTP status is 200.
 */
export function playVerifiedExceptionSound(httpStatus = 200): void {
  if (httpStatus === 200) {
    playGavelSound();
  } else {
    console.warn(
      `[SoundEffects] Exception gavel sound suppressed: HTTP status ${httpStatus} is not 200 OK.`
    );
  }
}
