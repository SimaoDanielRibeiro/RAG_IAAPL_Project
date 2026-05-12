type LogoProps = {
  className?: string;
  showWordmark?: boolean;
  size?: number;
};

export function Logo({
  className = "",
  showWordmark = false,
  size = 28,
}: LogoProps) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <img
        src="/lumen-logo.png"
        alt="Lumen"
        width={size}
        height={size}
        draggable={false}
        className="shrink-0 select-none object-contain"
        style={{ width: size, height: size }}
      />
      {showWordmark && (
        <span className="text-[17px] font-semibold tracking-[-0.005em] text-primary">
          Lumen
        </span>
      )}
    </div>
  );
}
