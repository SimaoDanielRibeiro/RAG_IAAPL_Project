type LogoProps = {
  className?: string;
  showWordmark?: boolean;
  size?: number;
  wordmarkClass?: string;
};

export function Logo({
  className = "",
  showWordmark = false,
  size = 28,
  wordmarkClass = "text-[17px]",
}: LogoProps) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <img
        src="/logo.png"
        alt="Lumen"
        width={size}
        height={size}
        draggable={false}
        className="shrink-0 select-none object-contain"
        style={{ width: size, height: size }}
      />
      {showWordmark && (
        <span className={`font-semibold tracking-[-0.005em] text-primary ${wordmarkClass}`}>
          Lumen
        </span>
      )}
    </div>
  );
}
