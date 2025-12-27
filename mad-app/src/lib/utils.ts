// lib/utils.ts
import type { AgentName } from './types.js';

const DEBATER_COLORS = [
	// Renamed 'name' to 'colorName' to avoid collision when spreading
	{
		colorName: 'Blue',
		colorHex: '#3b82f6',
		bg: 'bg-blue-900/50',
		border: 'border-blue-500',
		text: 'text-blue-300',
		bubble: 'bg-blue-800/60',
		icon: 'text-blue-400'
	},
	{
		colorName: 'Red',
		colorHex: '#ef4444',
		bg: 'bg-red-900/50',
		border: 'border-red-500',
		text: 'text-red-300',
		bubble: 'bg-red-800/60',
		icon: 'text-red-400'
	},
	{
		colorName: 'Green',
		colorHex: '#10b981',
		bg: 'bg-green-900/50',
		border: 'border-green-500',
		text: 'text-green-300',
		bubble: 'bg-green-800/60',
		icon: 'text-green-400'
	},
	{
		colorName: 'Purple',
		colorHex: '#8b5cf6',
		bg: 'bg-purple-900/50',
		border: 'border-purple-500',
		text: 'text-purple-300',
		bubble: 'bg-purple-800/60',
		icon: 'text-purple-400'
	},
	{
		colorName: 'Pink',
		colorHex: '#ec4899',
		bg: 'bg-pink-900/50',
		border: 'border-pink-500',
		text: 'text-pink-300',
		bubble: 'bg-pink-800/60',
		icon: 'text-pink-400'
	},
	{
		colorName: 'Teal',
		colorHex: '#14b8a6',
		bg: 'bg-teal-900/50',
		border: 'border-teal-500',
		text: 'text-teal-300',
		bubble: 'bg-teal-800/60',
		icon: 'text-teal-400'
	}
];

export const getAgentUI = (name: AgentName) => {
	if (name === 'Judge') {
		return {
			name: 'Judge', // Explicitly set the agent's name
			// ...DEBATER_COLORS[0], // Spreads color properties like bg, border, etc.
			colorName: 'Yellow',
			colorHex: '#eab308',
			bg: 'bg-yellow-900/50',
			border: 'border-yellow-500',
			text: 'text-yellow-300',
			bubble: 'bg-yellow-800/60 border border-yellow-500/50',
			icon: 'text-yellow-400',
			container: 'justify-start',
			rounded: 'rounded-br-none',
			isLeft: true
		};
	}

	if (name === 'user') {
		return {
			name: 'user', // Explicitly set the agent's name
			// ...DEBATER_COLORS[0],
			colorName: 'Gray',
			colorHex: '#9ca3af',
			bg: 'bg-gray-700/80',
			border: 'border-gray-600',
			text: 'text-gray-300',
			bubble: 'bg-gray-700/80 text-center italic',
			icon: 'text-gray-400',
			container: 'justify-center',
			rounded: 'rounded-lg',
			isLeft: true
		};
	}

	const match = name.match(/Debater_([A-Z])/);
	if (match) {
		const letter = match[1];
		const index = letter.charCodeAt(0) - 'A'.charCodeAt(0);
		const colors = DEBATER_COLORS[index % DEBATER_COLORS.length];
		const isLeft = index % 2 === 0; // A, C, E... on left

		return {
			name, // Set the name property using the AgentName variable
			...colors,
			container: isLeft ? 'justify-start' : 'justify-end',
			rounded: isLeft ? 'rounded-br-none' : 'rounded-bl-none',
			isLeft: isLeft
		};
	}

	// Default fallback
	return {
		name: 'Agent', // Explicitly set the fallback name
		...DEBATER_COLORS[0],
		container: 'justify-start',
		rounded: 'rounded-br-none',
		isLeft: true
	};
};
