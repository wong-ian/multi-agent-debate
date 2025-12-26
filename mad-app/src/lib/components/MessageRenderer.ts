import * as d3 from 'd3';
import type { Message } from '$lib/types.js';
export class MessageRenderer {
	svgId: string;
	width: number;
	height: number;
	padding: { top: number; right: number; bottom: number; left: number } = {
		top: 5,
		right: 1,
		bottom: 5,
		left: 1
	};
	handleMessageClicked: (event: any, d: any) => void;
	constructor(
		svgId: string,
		width: number,
		height: number,
		handleMessageClicked: (event: any, d: any) => void = () => {}
	) {
		this.svgId = svgId;
		this.width = width;
		this.height = height;
		this.handleMessageClicked = handleMessageClicked;
		const svg = d3.select<SVGSVGElement, unknown>(`#${this.svgId}`);
		svg.attr(
			'viewBox',
			`${-this.padding.left} ${-this.padding.top} ${this.width + this.padding.left + this.padding.right} ${this.height + this.padding.top + this.padding.bottom}`
		);
		svg.append('g').attr('class', 'message-group');
	}

	update(messages: Message[], speaker_num: number, metadata: any) {
		console.log(this.svgId, messages);
		const svg = d3.select<SVGSVGElement, unknown>(`#${this.svgId}`);
		if (svg.empty()) {
			console.warn(`SVG element with id ${this.svgId} not found.`);
			return;
		}

		// Example: Draw a simple circle in the center of the SVG
		// svg
		// 	.append('rect')
		// 	.attr('width', this.width)
		// 	.attr('height', this.height)
		// 	.attr('fill', 'none')
		// 	.attr('stroke', 'gray')
		// 	.attr('stroke-width', 2);
		// svg
		// 	.append('circle')
		// 	.attr('cx', this.width / 2)
		// 	.attr('cy', this.height / 2)
		// 	.attr('r', 2)
		// 	.attr('fill', 'gray');
		const rect_width = this.width / (speaker_num || 1);
		svg
			.select('.message-group')
			.selectAll('rect')
			.data(messages)
			.join('rect')
			.attr('x', (d) => rect_width * (d.round_inner_index ?? 1))
			.attr('y', (d, i) => 0)
			.attr('width', rect_width)
			.attr('height', this.height)
			.attr('fill', metadata?.color || '#f3f3f3')
			.attr('stroke', 'white')
			.attr('stroke-width', 2)
			.attr('cursor', 'pointer')
			.on('mouseover', function () {
				d3.select(this).attr('fill', d3.rgb(metadata?.color || '#f3f3f3').darker(1));
			})
			.on('mouseout', function () {
				d3.select(this).attr('fill', metadata?.color || '#f3f3f3');
			})
			.on('click', this.handleMessageClicked);
	}
}
