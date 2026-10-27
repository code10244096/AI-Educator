/** 待复核（AI 没把握、score_pending）不把 0 分当真分。 */

export const isScorePending = (s) => Boolean(s?.score_pending)

export const isGraded = (s) => s?.status === 'completed' && s?.score !== null && s?.score !== undefined

export const needsReview = (s) => isGraded(s) && s.review_status === 'pending_review'

export function scoreLabel(s, { unit = ' 分', empty = '-' } = {}) {
  if (isScorePending(s)) return '待复核'
  if (!isGraded(s) || s.score === null || s.score === undefined) return empty
  return `${s.score}${unit}`
}
