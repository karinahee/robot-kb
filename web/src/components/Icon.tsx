import Image from 'next/image';

interface IconProps {
  name: string;
  size?: number;
  className?: string;
}

/** 统一 icon 组件，从 /public/icons 加载 SVG */
export function Icon({ name, size = 18, className = '' }: IconProps) {
  return (
    <Image
      src={`/icons/${name}.svg`}
      alt={name}
      width={size}
      height={size}
      className={className}
    />
  );
}
