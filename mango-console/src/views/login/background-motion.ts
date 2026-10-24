export function startLoginBackgroundMotion(track: HTMLElement) {
  const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)')
  let animation: Animation | undefined

  function sync(restart = false) {
    if (motionPreference.matches) {
      animation?.cancel()
      animation = undefined
      return
    }
    if (document.hidden) {
      animation?.pause()
      return
    }
    if (restart || !animation || animation.playState === 'idle' || animation.playState === 'finished') {
      // 页面从后台或页面缓存恢复时重建动画，保留进度，避免合成层停在旧帧。
      const currentTime = animation?.currentTime
      animation?.cancel()
      animation = track.animate(
        [
          { transform: 'rotate(7deg) translateY(0)' },
          { transform: 'rotate(7deg) translateY(-50%)' },
        ],
        { duration: 160_000, iterations: Infinity, easing: 'linear' }
      )
      if (typeof currentTime === 'number') animation.currentTime = currentTime
    }
    animation.play()
  }

  const resume = () => sync(true)
  document.addEventListener('visibilitychange', resume)
  window.addEventListener('pageshow', resume)
  track.addEventListener('load', resume, { capture: true })
  motionPreference.addEventListener('change', resume)
  sync()

  return () => {
    document.removeEventListener('visibilitychange', resume)
    window.removeEventListener('pageshow', resume)
    track.removeEventListener('load', resume, { capture: true })
    motionPreference.removeEventListener('change', resume)
    animation?.cancel()
  }
}
