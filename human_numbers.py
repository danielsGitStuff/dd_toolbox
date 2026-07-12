class HumanNumbers:
    @staticmethod
    def large_counts(num: int) -> str:
        """Formats an integer into a human readable count string like 1.5k, 2.2M, 1.5B."""
        if num < 1000:
            return str(num)
        elif num < 1_000_000:
            return f"{num / 1000:.1f}k"
        elif num < 1_000_000_000:
            return f"{num / 1_000_000:.1f}M"
        else:
            return f"{num / 1_000_000_000:.1f}B"

    @staticmethod
    def large_byte_sizes(num: int) -> str:
        """Formats an integer into a human readable byte size string like 1.5kb, 2.2mb."""
        if num < 1024:
            return f"{num}b"
        elif num < 1024**2:
            return f"{num / 1024:.1f}kb"
        elif num < 1024**3:
            return f"{num / 1024**2:.1f}mb"
        else:
            return f"{num / 1024**3:.1f}gb"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format a duration given in seconds, e.g. 1.5 -> '1s 500ms'."""
        return HumanNumbers.format_duration_ms(seconds * 1000)

    @staticmethod
    def format_duration_ms(milliseconds: float) -> str:
        """Format a duration given in milliseconds, e.g. 1500 -> '1s 500ms'."""
        total_ms = round(milliseconds)
        ms = total_ms % 1000
        total_s = total_ms // 1000
        s = total_s % 60
        total_m = total_s // 60
        m = total_m % 60
        total_h = total_m // 60
        h = total_h % 24
        total_d = total_h // 24
        y = total_d // 365
        remaining_d = total_d % 365
        mo = remaining_d // 30
        d = remaining_d % 30

        units = [(y, 'y'), (mo, 'mo'), (d, 'd'), (h, 'h'), (m, 'm'), (s, 's'), (ms, 'ms')]

        start = len(units) - 1  # default: ms
        for i, (val, _) in enumerate(units):
            if val > 0:
                start = i
                break

        selected = units[start : start + 3]
        return ' '.join(f"{val}{suffix}" for val, suffix in selected)
