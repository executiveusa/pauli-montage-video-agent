/**
 * Build a stable idempotency key for a consequential external side effect.
 * The key is safe to pass to an external API or persist in an ops receipt.
 */
export function sideEffectKey(taskID, action, subject) {
  if (!taskID || !action || !subject) {
    throw new TypeError('taskID, action, and subject are required');
  }
  return `${taskID}:${action}:${subject}`;
}

/**
 * Execute an external side effect inside an Absurd-style checkpoint.
 * Replays return the recorded value rather than invoking `run` again.
 */
export async function checkpointedSideEffect(ctx, stepName, run) {
  return ctx.step(stepName, async () => {
    const idempotencyKey = sideEffectKey(ctx.taskID, 'side-effect', stepName);
    return run(idempotencyKey);
  });
}
