import type { Config } from "tailwindcss";

export default {
	darkMode: ["class"],
	content: [
		"./pages/**/*.{ts,tsx}",
		"./components/**/*.{ts,tsx}",
		"./app/**/*.{ts,tsx}",
		"./src/**/*.{ts,tsx}",
	],
	prefix: "",
	theme: {
		container: {
			center: true,
			padding: '2rem',
			screens: {
				'2xl': '1400px'
			}
		},
		extend: {
			colors: {
				border: 'hsl(var(--border))',
				input: 'hsl(var(--input))',
				ring: 'hsl(var(--ring))',
				background: 'hsl(var(--background))',
				foreground: 'hsl(var(--foreground))',
				primary: {
					DEFAULT: 'hsl(var(--primary))',
					foreground: 'hsl(var(--primary-foreground))'
				},
				secondary: {
					DEFAULT: 'hsl(var(--secondary))',
					foreground: 'hsl(var(--secondary-foreground))'
				},
				destructive: {
					DEFAULT: 'hsl(var(--destructive))',
					foreground: 'hsl(var(--destructive-foreground))'
				},
				muted: {
					DEFAULT: 'hsl(var(--muted))',
					foreground: 'hsl(var(--muted-foreground))'
				},
				accent: {
					DEFAULT: 'hsl(var(--accent))',
					foreground: 'hsl(var(--accent-foreground))'
				},
				popover: {
					DEFAULT: 'hsl(var(--popover))',
					foreground: 'hsl(var(--popover-foreground))'
				},
				card: {
					DEFAULT: 'hsl(var(--card))',
					foreground: 'hsl(var(--card-foreground))'
				},
				// MARTA Transit System Colors
				marta: {
					blue: 'hsl(var(--marta-blue))',
					gold: 'hsl(var(--marta-gold))',
					green: 'hsl(var(--marta-green))',
					orange: 'hsl(var(--marta-orange))',
					red: 'hsl(var(--marta-red))'
				},
				// Transit Demand Status
				demand: {
					high: 'hsl(var(--high-demand))',
					medium: 'hsl(var(--medium-demand))',
					low: 'hsl(var(--low-demand))',
					optimal: 'hsl(var(--optimal))'
				}
			},
			fontFamily: {
				sans: ['Inter', 'system-ui', 'sans-serif']
			},
			backgroundImage: {
				'gradient-demand': 'var(--gradient-demand)',
				'gradient-primary': 'var(--gradient-primary)',
				'gradient-overlay': 'var(--gradient-overlay)'
			},
			boxShadow: {
				'transit': 'var(--shadow-transit)',
				'elegant': 'var(--shadow-lg)'
			},
			transitionDuration: {
				'fast': 'var(--animation-fast)',
				'smooth': 'var(--animation-smooth)',
				'slow': 'var(--animation-slow)'
			},
			borderRadius: {
				lg: 'var(--radius)',
				md: 'calc(var(--radius) - 2px)',
				sm: 'calc(var(--radius) - 4px)'
			},
			keyframes: {
				'accordion-down': {
					from: { height: '0' },
					to: { height: 'var(--radix-accordion-content-height)' }
				},
				'accordion-up': {
					from: { height: 'var(--radix-accordion-content-height)' },
					to: { height: '0' }
				},
				'arrival-pulse': {
					'0%, 100%': { opacity: '1', transform: 'scale(1)' },
					'50%': { opacity: '0.5', transform: 'scale(1.4)' }
				},
				'count-pulse': {
					'0%, 100%': { transform: 'scale(1)' },
					'50%': { transform: 'scale(1.06)' }
				},
				'shimmer': {
					'0%': { backgroundPosition: '-200% 0' },
					'100%': { backgroundPosition: '200% 0' }
				},
				'slide-up': {
					from: { transform: 'translateY(100%)', opacity: '0' },
					to: { transform: 'translateY(0)', opacity: '1' }
				},
				'fade-in': {
					from: { opacity: '0', transform: 'translateY(8px)' },
					to: { opacity: '1', transform: 'translateY(0)' }
				}
			},
			animation: {
				'accordion-down': 'accordion-down 0.2s ease-out',
				'accordion-up': 'accordion-up 0.2s ease-out',
				'arrival-pulse': 'arrival-pulse 1.4s ease-in-out infinite',
				'count-pulse': 'count-pulse 1s ease-in-out infinite',
				'shimmer': 'shimmer 1.5s infinite',
				'slide-up': 'slide-up 0.3s ease-out',
				'fade-in': 'fade-in 0.25s ease-out'
			}
		}
	},
	plugins: [require("tailwindcss-animate")],
} satisfies Config;
