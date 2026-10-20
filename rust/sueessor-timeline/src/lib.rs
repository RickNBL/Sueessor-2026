//! Cálculos de calendário usados pelo portal, caso a extensão WASM seja habilitada.
//! A linha do tempo visível possui fallback em TypeScript e não exige Rust na Vercel.
const FOUNDATION_YEAR: u32 = 2002;
const FOUNDATION_MONTH: u32 = 4;
const FOUNDATION_DAY: u32 = 12;

#[no_mangle]
pub extern "C" fn full_years_since_foundation(year: u32, month: u32, day: u32) -> u32 {
    if year < FOUNDATION_YEAR || month < 1 || month > 12 || day < 1 || day > 31 {
        return 0;
    }
    let years = year - FOUNDATION_YEAR;
    if month < FOUNDATION_MONTH || (month == FOUNDATION_MONTH && day < FOUNDATION_DAY) {
        years.saturating_sub(1)
    } else {
        years
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn anniversary_is_exact() {
        assert_eq!(full_years_since_foundation(2002, 4, 12), 0);
        assert_eq!(full_years_since_foundation(2026, 4, 11), 23);
        assert_eq!(full_years_since_foundation(2026, 4, 12), 24);
    }
}
