//! Fallible, thread-safe lazy initialization.

use std::sync::{Mutex, OnceLock, PoisonError};

/// A value built on first successful use and shared afterwards.
///
/// A failed build returns its error, and a later call retries. This stands in
/// for `OnceLock::get_or_try_init`, which is not stable on the crate's minimum
/// Rust version.
pub struct LazyCache<T> {
    value: OnceLock<T>,
    init: Mutex<()>,
}

impl<T> Default for LazyCache<T> {
    fn default() -> Self {
        Self {
            value: OnceLock::new(),
            init: Mutex::new(()),
        }
    }
}

impl<T> LazyCache<T> {
    /// The value, if it has been built.
    pub fn get(&self) -> Option<&T> {
        self.value.get()
    }

    /// The value, building it with `build` if no call has succeeded yet.
    /// Concurrent callers wait for one build instead of racing.
    pub fn get_or_try_init<E>(&self, build: impl FnOnce() -> Result<T, E>) -> Result<&T, E> {
        if let Some(value) = self.value.get() {
            return Ok(value);
        }
        // The lock guards no data, so a panicked build leaves nothing to repair.
        let _guard = self.init.lock().unwrap_or_else(PoisonError::into_inner);
        if let Some(value) = self.value.get() {
            return Ok(value);
        }
        let value = build()?;
        Ok(self.value.get_or_init(|| value))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_failed_build_is_retried_and_a_success_is_kept() {
        let cache = LazyCache::default();
        assert_eq!(cache.get_or_try_init(|| Err("no")), Err("no"));
        assert_eq!(cache.get(), None);
        assert_eq!(cache.get_or_try_init(|| Ok::<_, ()>(1)), Ok(&1));
        assert_eq!(cache.get_or_try_init(|| Ok::<_, ()>(2)), Ok(&1));
    }
}
