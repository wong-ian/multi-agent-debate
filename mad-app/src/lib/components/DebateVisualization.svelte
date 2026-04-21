<script lang="ts">
    import { onMount, createEventDispatcher } from 'svelte';
    import * as d3 from 'd3';
    import type { Message } from '$lib/types.ts';

    export let messages: Message[] = [];
    export let roundAnalyses: Record<number, any> = {};
    export let roundKeywords: Record<number, { term: string; score: number }[]> = {};
    export let regeneratedRounds: Record<number, { mastFailures: string[]; humanInput: string }> = {};
    export let isPaused: boolean = false;
    export let currentRound: number = 0;

    const dispatch = createEventDispatcher<{
        regenerate: { roundNumber: number; mastFailures: string[]; humanInput: string };
    }>();

    // DOM refs
    let swimlaneContainer: HTMLDivElement;
    let verticalContainer: HTMLDivElement;

    // Modal state
    let modalOpen = false;
    let modalData: any = null;

    // Intervention state (for vertical thread)
    let interventionRound: number | null = null;
    let interventionInput: string = '';
    let isRegenerating: boolean = false;

    // Y positions for positioning overlay and scroll anchors
    let roundSepY: Record<number, number> = {};
    let verticalNodeY: Record<string, number> = {};

    const FONT = "'Calibri', 'Calibri Regular', sans-serif";

    const REFERENTIAL_FAILURE_IDS = new Set(['1.3', '1.4', '2.5']);
    let swimCardPositions: Record<string, { x: number; y: number }> = {};
    let vertCardPositions: Record<string, { x: number; y: number }> = {};

    const COLORS: Record<string, string> = {
        Debater_A: '#6366f1',
        Debater_B: '#10b981',
        Debater_C: '#a855f7',
        Debater_D: '#ec4899',
        Debater_E: '#14b8a6',
        Debater_F: '#f97316',
        Judge: '#f59e0b',
        Human_Moderator: '#6b7280',
        Memory_Cell: '#d97706',
        Failure: '#ef4444'
    };

    const getColor = (agent: string) => COLORS[agent] || '#6b7280';

    function buildMergedData() {
        const realMessages = messages.filter(m => m.round > 0);
        const rounds = [...new Set(realMessages.map(m => m.round))].sort((a, b) => a - b);
        const merged: any[] = [];

        rounds.forEach((round, roundIdx) => {
            // Synthetic "Human_Moderator" directive card for rounds 2+
            if (roundIdx > 0) {
                merged.push({
                    round,
                    agent: 'Human_Moderator',
                    content: `Round ${round} directive: Continue the debate with focus on addressing previous points.`,
                    analysis: { failures: [], summary: 'Moderation guidance.' },
                    hasFailure: false,
                    shortSummary: `Round ${round} directive: Continue the debate with focus on addressing previous points.`
                });
            }

            const roundMsgs = realMessages.filter(m => m.round === round);
            roundMsgs.forEach(msg => {
                const roundAnalysis = roundAnalyses[round] || { failures: [], summary: 'Analysis pending...' };
                const hasFailure = roundAnalysis.failures?.some((f: any) => f.detected) ?? false;
                let summary = msg.content.split(/[.!?]/)[0] + '.';
                if (summary.length > 100) summary = summary.substring(0, 97) + '...';

                merged.push({
                    ...msg,
                    analysis: roundAnalysis,
                    hasFailure,
                    shortSummary: summary
                });
            });
        });

        return merged;
    }

    function getAgents(mergedData: any[]) {
        const seen = new Set<string>();
        const agents: string[] = [];
        mergedData.forEach(d => {
            if (d.agent !== 'Human_Moderator' && !seen.has(d.agent)) {
                seen.add(d.agent);
                agents.push(d.agent);
            }
        });
        return agents;
    }

    function openModal(data: any) {
        modalData = data;
        modalOpen = true;
    }

    function closeModal() {
        modalOpen = false;
        modalData = null;
    }

    function jumpToThread() {
        if (!modalData) return;
        const key = `${modalData.agent}-r${modalData.round}`;
        const anchor = document.getElementById(`vthread-${key}`);
        anchor?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        closeModal();
    }

    // Wrap text across multiple SVG <text> lines
    function wrapText(g: any, text: string, x: number, startY: number, maxWidthChars: number, lineHeight: number, maxLines: number, attrs: Record<string, string>) {
        const words = text.split(' ');
        let line = '';
        let lineNum = 0;
        words.forEach((word: string, idx: number) => {
            if (lineNum >= maxLines) return;
            const testLine = line + word + ' ';
            if (testLine.length > maxWidthChars && idx > 0) {
                const el = g.append('text').text(line.trim()).attr('x', x).attr('y', startY + lineNum * lineHeight);
                Object.entries(attrs).forEach(([k, v]) => el.attr(k, v));
                el.style('font-family', FONT);
                line = word + ' ';
                lineNum++;
            } else {
                line = testLine;
            }
        });
        if (lineNum < maxLines && line.trim()) {
            const el = g.append('text').text(line.trim()).attr('x', x).attr('y', startY + lineNum * lineHeight);
            Object.entries(attrs).forEach(([k, v]) => el.attr(k, v));
            el.style('font-family', FONT);
        }
    }

    function renderSwimlane() {
        if (!swimlaneContainer) return;
        const svgSel = d3.select(swimlaneContainer).select<SVGSVGElement>('svg');
        svgSel.selectAll('*').remove();
        swimCardPositions = {};

        const MERGED_DATA = buildMergedData();
        if (MERGED_DATA.length === 0) return;

        const agents = getAgents(MERGED_DATA);
        const rounds = [...new Set(
            MERGED_DATA.filter(d => d.agent !== 'Human_Moderator').map(d => d.round)
        )].sort((a, b) => a - b);

        const margin = { top: 40, right: 60, bottom: 140, left: 130 };
        const laneHeight = 90;
        const swimlaneHeight = 500;
        const boxWidth = 220;
        const boxSpacing = 50;
        const staggerOffset = 80;
        const totalWidth = Math.max(
            1400,
            rounds.length * (boxWidth + boxSpacing + staggerOffset * agents.length) + margin.left + margin.right
        );

        const svg = svgSel
            .attr('width', totalWidth)
            .attr('height', swimlaneHeight)
            .style('font-family', FONT);

        // Arrowhead marker for referential arrows
        svg.append('defs').append('marker')
            .attr('id', 'arrowhead-swimlane')
            .attr('viewBox', '0 0 10 10')
            .attr('refX', 10).attr('refY', 5)
            .attr('markerWidth', 5).attr('markerHeight', 5)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M 0 0 L 10 5 L 0 10 z')
            .attr('fill', '#ef4444');

        const yScale = d3.scaleBand()
            .domain(agents)
            .range([margin.top, agents.length * laneHeight + margin.top])
            .padding(0.2);

        // Lane labels
        svg.selectAll('.lane-label')
            .data(agents)
            .join('text')
            .attr('x', margin.left - 15)
            .attr('y', d => yScale(d)! + yScale.bandwidth() / 2)
            .attr('dy', '0.35em')
            .attr('text-anchor', 'end')
            .attr('fill', '#9CA3AF')
            .attr('font-size', '13px')
            .attr('font-weight', '700')
            .style('font-family', FONT)
            .text(d => d.replace('_', ' '));

        // Lane backgrounds
        svg.selectAll('.lane-bg')
            .data(agents)
            .join('rect')
            .attr('x', margin.left)
            .attr('y', d => yScale(d)!)
            .attr('width', totalWidth - margin.left - margin.right)
            .attr('height', yScale.bandwidth())
            .attr('fill', '#1f2937')
            .attr('stroke', '#374151')
            .attr('stroke-width', 1)
            .attr('rx', 4);

        // Column headers (round numbers + regenerated badge)
        const colWidth = boxWidth + boxSpacing + staggerOffset * agents.length;
        rounds.forEach((round: number, roundIndex: number) => {
            const x = margin.left + roundIndex * colWidth + 15;
            const isRegen = !!regeneratedRounds[round];

            const hg = svg.append('g');
            hg.append('text')
                .text(`Round ${round}${isRegen ? ' ↺' : ''}`)
                .attr('x', x + (boxWidth + staggerOffset * agents.length) / 2)
                .attr('y', margin.top - 18)
                .attr('text-anchor', 'middle')
                .attr('font-size', '11px')
                .attr('font-weight', 'bold')
                .attr('fill', isRegen ? '#d97706' : '#6b7280')
                .style('font-family', FONT);
        });

        // Message cards (exclude Human_Moderator from swimlane grid)
        const boxes = svg.selectAll('.swimlane-box')
            .data(MERGED_DATA.filter(d => d.agent !== 'Human_Moderator'))
            .join('g')
            .attr('class', 'swimlane-box')
            .style('cursor', 'pointer')
            .on('click', (_e: Event, d: any) => openModal(d));

        boxes.each(function(d: any) {
            const g = d3.select(this);
            const roundIndex = rounds.indexOf(d.round);
            const agentIndex = agents.indexOf(d.agent);
            const agentStagger = agentIndex * staggerOffset;
            const x = margin.left + roundIndex * colWidth + 15 + agentStagger;
            const y = yScale(d.agent)! + (yScale.bandwidth() - 64) / 2;

            // Card background
            g.append('rect')
                .attr('x', x).attr('y', y)
                .attr('width', boxWidth).attr('height', 64)
                .attr('rx', 8)
                .attr('fill', '#1f2937')
                .attr('stroke', d.hasFailure ? COLORS.Failure : getColor(d.agent))
                .attr('stroke-width', d.hasFailure ? 3 : 2);

            // Color stripe
            g.append('rect')
                .attr('x', x).attr('y', y)
                .attr('width', boxWidth).attr('height', 5)
                .attr('rx', 8)
                .attr('fill', getColor(d.agent))
                .attr('opacity', 0.9);

            // Round badge
            g.append('text')
                .text(`R${d.round}`)
                .attr('x', x + boxWidth - 8).attr('y', y + 16)
                .attr('text-anchor', 'end')
                .attr('font-size', '10px').attr('font-weight', 'bold')
                .attr('fill', '#6b7280')
                .style('font-family', FONT);

            // Summary text
            wrapText(g, d.shortSummary, x + 8, y + 18, Math.floor((boxWidth - 16) / 6), 12, 3, {
                'font-size': '11px', fill: '#d1d5db', 'font-style': 'italic'
            });

            // Failure indicator dot
            if (d.hasFailure) {
                g.append('circle')
                    .attr('cx', x + 8).attr('cy', y + 10)
                    .attr('r', 4).attr('fill', COLORS.Failure);
            }

            // Store card center for referential arrows
            swimCardPositions[`${d.round}_${d.agent}`] = { x: x + boxWidth / 2, y: y + 32 };
        });

        // Keyword sections below swim lanes
        const keywordY = agents.length * laneHeight + margin.top + 20;

        rounds.forEach((round: number, roundIndex: number) => {
            const x = margin.left + roundIndex * colWidth + 15;
            const keywords = roundKeywords[round] || [];

            const kg = svg.append('g');

            kg.append('rect')
                .attr('x', x).attr('y', keywordY)
                .attr('width', boxWidth + staggerOffset * agents.length).attr('height', 100)
                .attr('rx', 8)
                .attr('fill', '#111827')
                .attr('stroke', '#374151').attr('stroke-width', 1);

            kg.append('text')
                .text('KEY TOPICS:')
                .attr('x', x + 10).attr('y', keywordY + 18)
                .attr('font-size', '9px').attr('font-weight', 'bold')
                .attr('fill', keywords.length > 0 ? '#6b7280' : '#4b5563')
                .style('font-family', FONT);

            if (keywords.length === 0) {
                kg.append('text')
                    .text('Analyzing...')
                    .attr('x', x + 10).attr('y', keywordY + 36)
                    .attr('font-size', '9px').attr('fill', '#4b5563')
                    .attr('font-style', 'italic')
                    .style('font-family', FONT);
            } else {
                const bubblePadding = 12;
                const bubbleHeight = 16;
                const bubbleSpacing = 6;
                const maxRowWidth = boxWidth + staggerOffset * agents.length - 20;

                let curX = x + 10;
                let curY = keywordY + 30;

                keywords.forEach((kw: { term: string; score: number }) => {
                    const approxWidth = kw.term.length * 6.5 + bubblePadding;
                    if ((curX - (x + 10)) + approxWidth > maxRowWidth && curX > x + 10) {
                        curY += bubbleHeight + 4;
                        curX = x + 10;
                    }

                    kg.append('rect')
                        .attr('x', curX).attr('y', curY)
                        .attr('width', approxWidth).attr('height', bubbleHeight)
                        .attr('rx', 8)
                        .attr('fill', '#1f2937').attr('stroke', '#374151').attr('stroke-width', 1);

                    kg.append('text')
                        .text(kw.term)
                        .attr('x', curX + bubblePadding / 2).attr('y', curY + 11)
                        .attr('font-size', '9px').attr('fill', '#9ca3af')
                        .style('font-family', FONT);

                    curX += approxWidth + bubbleSpacing;
                });
            }
        });

        // Draw referential arrows for failures 1.3, 1.4, 2.5
        Object.values(roundAnalyses).forEach((analysis: any) => {
            if (!analysis?.failures) return;
            analysis.failures
                .filter((f: any) => f.detected && REFERENTIAL_FAILURE_IDS.has(f.id) && f.failedBy && f.refersTo)
                .forEach((f: any) => {
                    const from = swimCardPositions[`${f.failedBy.round}_${f.failedBy.agent}`];
                    const to = swimCardPositions[`${f.refersTo.round}_${f.refersTo.agent}`];
                    if (!from || !to) return;

                    let pathD: string;
                    if (f.failedBy.round > f.refersTo.round) {
                        const controlY = Math.min(from.y, to.y) - 60;
                        pathD = `M ${from.x} ${from.y} C ${from.x} ${controlY}, ${to.x} ${controlY}, ${to.x} ${to.y}`;
                    } else {
                        const midX = (from.x + to.x) / 2;
                        pathD = `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`;
                    }

                    svg.append('path')
                        .attr('d', pathD)
                        .attr('fill', 'none')
                        .attr('stroke', '#ef4444')
                        .attr('stroke-width', 2.5)
                        .attr('opacity', 0.6)
                        .attr('class', 'drift-line')
                        .attr('marker-end', 'url(#arrowhead-swimlane)');
                });
        });
    }

    function renderVertical() {
        if (!verticalContainer) return;
        const containerWidth = verticalContainer.clientWidth || 800;
        const MERGED_DATA = buildMergedData();
        if (MERGED_DATA.length === 0) return;

        const rounds = [...new Set(MERGED_DATA.map(d => d.round))].sort((a, b) => a - b);
        const dataByRound = rounds.map(round => ({
            round,
            messages: MERGED_DATA.filter(d => d.round === round)
        }));

        const nodeHeight = 150;
        const memCellHeight = 180;
        const gap = 40;
        const roundSeparatorHeight = 80;
        // Extra space for the intervention button when paused
        const interventionSlotHeight = 48;

        // Total height accounts for memory cells and intervention slots
        const totalHeight = dataByRound.reduce((sum, rd) => {
            const hasMemCell = !!regeneratedRounds[rd.round];
            const hasIntervention = isPaused && rd.round === currentRound && rd.round > 1;
            return sum + rd.messages.length * (nodeHeight + gap) + roundSeparatorHeight
                + (hasMemCell ? memCellHeight + gap : 0)
                + (hasIntervention ? interventionSlotHeight : 0);
        }, 100);

        const svgSel = d3.select(verticalContainer).select<SVGSVGElement>('svg');
        svgSel.selectAll('*').remove();
        vertCardPositions = {};
        svgSel
            .attr('height', totalHeight)
            .attr('width', '100%')
            .style('font-family', FONT);

        // Arrowhead marker for referential arrows
        svgSel.append('defs').append('marker')
            .attr('id', 'arrowhead-vertical')
            .attr('viewBox', '0 0 10 10')
            .attr('refX', 10).attr('refY', 5)
            .attr('markerWidth', 4).attr('markerHeight', 4)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M 0 0 L 10 5 L 0 10 z')
            .attr('fill', '#ef4444');

        const centerX = containerWidth / 2;

        // Central spine
        svgSel.append('line')
            .attr('x1', centerX).attr('y1', 20)
            .attr('x2', centerX).attr('y2', totalHeight - 20)
            .attr('stroke', '#374151').attr('stroke-width', 2)
            .attr('stroke-dasharray', '8 8');

        let currentY = 60;
        const newRoundSepY: Record<number, number> = {};
        const newVerticalNodeY: Record<string, number> = {};

        dataByRound.forEach((roundData, roundIndex) => {
            const isRegen = !!regeneratedRounds[roundData.round];
            const regenData = regeneratedRounds[roundData.round];

            // Round separator and label (from round 2 onward)
            if (roundIndex > 0) {
                svgSel.append('line')
                    .attr('x1', centerX - 400).attr('y1', currentY - 40)
                    .attr('x2', centerX + 400).attr('y2', currentY - 40)
                    .attr('stroke', isRegen ? '#92400e' : '#4b5563').attr('stroke-width', 2)
                    .attr('stroke-dasharray', '10 5');

                svgSel.append('text')
                    .text(`ROUND ${roundData.round}${isRegen ? ' — REGENERATED ↺' : ''}`)
                    .attr('x', centerX).attr('y', currentY - 15)
                    .attr('text-anchor', 'middle')
                    .attr('font-size', '12px').attr('font-weight', 'bold')
                    .attr('fill', isRegen ? '#d97706' : '#6b7280')
                    .style('font-family', FONT);

                // Store Y for the intervention overlay positioning
                newRoundSepY[roundData.round] = currentY - 15;

                // Intervene button — only for current paused round
                if (isPaused && roundData.round === currentRound) {
                    const btnWidth = 160;
                    const btnHeight = 32;
                    const btnX = centerX - btnWidth / 2;
                    const btnY = currentY + 2;

                    const bg = svgSel.append('g')
                        .style('cursor', 'pointer')
                        .on('click', () => { interventionRound = roundData.round; });

                    bg.append('rect')
                        .attr('x', btnX).attr('y', btnY)
                        .attr('width', btnWidth).attr('height', btnHeight)
                        .attr('rx', 8)
                        .attr('fill', '#1c1208')
                        .attr('stroke', '#d97706').attr('stroke-width', 1.5);

                    bg.append('text')
                        .text(`⚡ Intervene on Round ${roundData.round}`)
                        .attr('x', centerX).attr('y', btnY + 21)
                        .attr('text-anchor', 'middle')
                        .attr('font-size', '11px').attr('font-weight', 'bold')
                        .attr('fill', '#fbbf24')
                        .style('font-family', FONT);

                    currentY += interventionSlotHeight;
                }
            }

            currentY += roundSeparatorHeight;

            // MEMORY CELL — rendered to the LEFT for regenerated rounds
            if (isRegen && regenData) {
                const memX = centerX - 380;
                const memWidth = 340;
                const mg = svgSel.append('g')
                    .attr('transform', `translate(${memX}, ${currentY})`);

                // Card background
                mg.append('rect')
                    .attr('width', memWidth).attr('height', memCellHeight)
                    .attr('rx', 12)
                    .attr('fill', '#1c1008')
                    .attr('stroke', '#d97706')
                    .attr('stroke-width', 2);

                // Top stripe
                mg.append('rect')
                    .attr('width', memWidth).attr('height', 8)
                    .attr('rx', 4)
                    .attr('fill', '#d97706').attr('opacity', 0.9);

                // Header
                mg.append('text')
                    .text('⚡ MEMORY CELL')
                    .attr('x', 14).attr('y', 30)
                    .attr('font-size', '12px').attr('font-weight', '900')
                    .attr('fill', '#fbbf24')
                    .style('font-family', FONT);

                mg.append('text')
                    .text(`Round ${roundData.round} — Injected Context`)
                    .attr('x', 14).attr('y', 46)
                    .attr('font-size', '10px').attr('fill', '#92400e')
                    .style('font-family', FONT);

                // MAST failures list
                mg.append('text')
                    .text('MAST FAILURES:')
                    .attr('x', 14).attr('y', 66)
                    .attr('font-size', '9px').attr('font-weight', 'bold')
                    .attr('fill', '#d97706')
                    .style('font-family', FONT);

                const failures = regenData.mastFailures.slice(0, 4);
                if (failures.length === 0) {
                    mg.append('text')
                        .text('None detected')
                        .attr('x', 14).attr('y', 80)
                        .attr('font-size', '9px').attr('fill', '#6b7280')
                        .attr('font-style', 'italic')
                        .style('font-family', FONT);
                } else {
                    failures.forEach((f: string, i: number) => {
                        const label = f.length > 42 ? f.substring(0, 39) + '...' : f;
                        mg.append('text')
                            .text(`• ${label}`)
                            .attr('x', 14).attr('y', 80 + i * 14)
                            .attr('font-size', '9px').attr('fill', '#fca5a5')
                            .style('font-family', FONT);
                    });
                }

                // Human input
                const humanInputY = 80 + Math.min(failures.length, 4) * 14 + 10;
                mg.append('line')
                    .attr('x1', 14).attr('y1', humanInputY - 4)
                    .attr('x2', memWidth - 14).attr('y2', humanInputY - 4)
                    .attr('stroke', '#92400e').attr('stroke-width', 1);

                mg.append('text')
                    .text('HUMAN INPUT:')
                    .attr('x', 14).attr('y', humanInputY + 10)
                    .attr('font-size', '9px').attr('font-weight', 'bold')
                    .attr('fill', '#d97706')
                    .style('font-family', FONT);

                const inputText = regenData.humanInput || 'No additional direction provided.';
                const truncated = inputText.length > 80 ? inputText.substring(0, 77) + '...' : inputText;
                mg.append('foreignObject')
                    .attr('x', 14).attr('y', humanInputY + 14)
                    .attr('width', memWidth - 28).attr('height', 40)
                    .append('xhtml:div')
                    .style('color', '#fde68a')
                    .style('font-size', '10px')
                    .style('font-family', FONT)
                    .style('font-style', 'italic')
                    .style('line-height', '1.4')
                    .style('overflow', 'hidden')
                    .html(`"${truncated}"`);

                // Spine dot
                svgSel.append('circle')
                    .attr('cx', centerX)
                    .attr('cy', currentY + memCellHeight / 2)
                    .attr('r', 6)
                    .attr('fill', '#111827')
                    .attr('stroke', '#d97706')
                    .attr('stroke-width', 3);

                currentY += memCellHeight + gap;
            }

            roundData.messages.forEach((d: any) => {
                // Debaters on left, Judge/Moderator on right
                const isLeft = d.agent.startsWith('Debater_');
                const xOffset = isLeft ? centerX - 380 : centerX + 40;

                // Store Y for scroll anchors
                newVerticalNodeY[`${d.agent}-r${d.round}`] = currentY;

                const g = svgSel.append('g')
                    .attr('class', 'v-node')
                    .style('cursor', 'pointer')
                    .attr('transform', `translate(${xOffset}, ${currentY})`)
                    .on('click', () => openModal(d));

                // Card background
                g.append('rect')
                    .attr('width', 340).attr('height', nodeHeight)
                    .attr('rx', 12)
                    .attr('fill', '#1F2937')
                    .attr('stroke', d.hasFailure ? COLORS.Failure : '#374151')
                    .attr('stroke-width', d.hasFailure ? 3 : 1);

                // Color stripe
                g.append('rect')
                    .attr('width', 340).attr('height', 8)
                    .attr('rx', 4)
                    .attr('fill', getColor(d.agent)).attr('opacity', 0.8);

                // Agent name
                g.append('text')
                    .text(d.agent.replace('_', ' '))
                    .attr('x', 16).attr('y', 30)
                    .attr('font-size', '12px').attr('font-weight', '900')
                    .attr('fill', getColor(d.agent))
                    .style('font-family', FONT)
                    .style('text-transform', 'uppercase');

                // Round badge
                g.append('text')
                    .text(`Round ${d.round}`)
                    .attr('x', 324).attr('y', 30)
                    .attr('text-anchor', 'end')
                    .attr('font-size', '11px').attr('fill', '#6B7280')
                    .style('font-family', FONT);

                // Label
                g.append('text')
                    .text(d.agent === 'Human_Moderator' ? 'DIRECTIVE:' : 'ARGUMENT PREVIEW:')
                    .attr('x', 16).attr('y', 55)
                    .attr('font-size', '10px').attr('font-weight', 'bold')
                    .attr('fill', '#4B5563')
                    .style('font-family', FONT);

                // Preview text
                g.append('foreignObject')
                    .attr('x', 16).attr('y', 65)
                    .attr('width', 308).attr('height', 60)
                    .append('xhtml:div')
                    .style('color', '#d1d5db')
                    .style('font-size', '13px')
                    .style('line-height', '1.5')
                    .style('font-style', 'italic')
                    .style('font-family', FONT)
                    .style('overflow', 'hidden')
                    .html(`"${d.shortSummary}"`);

                // Failure banner
                if (d.hasFailure && d.agent !== 'Human_Moderator') {
                    g.append('rect')
                        .attr('y', 125).attr('x', 16)
                        .attr('width', 308).attr('height', 24)
                        .attr('rx', 4).attr('fill', '#7F1D1D');

                    g.append('text')
                        .text('⚠ MAST FAILURE DETECTED')
                        .attr('x', 170).attr('y', 141)
                        .attr('text-anchor', 'middle')
                        .attr('fill', '#FCA5A5')
                        .attr('font-size', '10px').attr('font-weight', '900')
                        .style('font-family', FONT);
                }

                // Center dot on spine
                svgSel.append('circle')
                    .attr('cx', centerX)
                    .attr('cy', currentY + nodeHeight / 2)
                    .attr('r', 6)
                    .attr('fill', '#111827')
                    .attr('stroke', d.hasFailure ? COLORS.Failure : '#374151')
                    .attr('stroke-width', 3);

                // Store card center for referential arrows
                vertCardPositions[`${d.round}_${d.agent}`] = {
                    x: xOffset + 170,
                    y: currentY + nodeHeight / 2
                };

                currentY += nodeHeight + gap;
            });
        });

        // Draw referential arrows for failures 1.3, 1.4, 2.5
        Object.values(roundAnalyses).forEach((analysis: any) => {
            if (!analysis?.failures) return;
            analysis.failures
                .filter((f: any) => f.detected && REFERENTIAL_FAILURE_IDS.has(f.id) && f.failedBy && f.refersTo)
                .forEach((f: any) => {
                    const from = vertCardPositions[`${f.failedBy.round}_${f.failedBy.agent}`];
                    const to = vertCardPositions[`${f.refersTo.round}_${f.refersTo.agent}`];
                    if (!from || !to) return;

                    const pathD = `M ${from.x} ${from.y} C ${centerX} ${from.y}, ${centerX} ${to.y}, ${to.x} ${to.y}`;

                    svgSel.append('path')
                        .attr('d', pathD)
                        .attr('fill', 'none')
                        .attr('stroke', '#ef4444')
                        .attr('stroke-width', 2.5)
                        .attr('opacity', 0.6)
                        .attr('class', 'drift-line')
                        .attr('marker-end', 'url(#arrowhead-vertical)');
                });
        });

        // Commit position maps reactively
        roundSepY = newRoundSepY;
        verticalNodeY = newVerticalNodeY;
    }

    function handleRegenerateClick() {
        if (!interventionRound) return;
        isRegenerating = true;
        const currentRoundAnalysis = roundAnalyses[interventionRound];
        const mastFailures: string[] = currentRoundAnalysis?.failures
            ?.filter((f: any) => f.detected)
            ?.map((f: any) => `${f.id}: ${f.name}`) || [];

        dispatch('regenerate', {
            roundNumber: interventionRound,
            mastFailures,
            humanInput: interventionInput
        });

        // Parent handles the async work; reset local state
        interventionRound = null;
        interventionInput = '';
        isRegenerating = false;
    }

    // Re-render whenever any reactive prop changes
    $: {
        const _m = messages;
        const _ra = roundAnalyses;
        const _rk = roundKeywords;
        const _rr = regeneratedRounds;
        const _ip = isPaused;
        const _cr = currentRound;
        if (swimlaneContainer && verticalContainer && _m.length > 0) {
            renderSwimlane();
            renderVertical();
        }
    }

    onMount(() => {
        if (messages.length > 0) {
            renderSwimlane();
            renderVertical();
        }

        const swimObs = new ResizeObserver(() => renderSwimlane());
        const vertObs = new ResizeObserver(() => renderVertical());
        swimObs.observe(swimlaneContainer);
        vertObs.observe(verticalContainer);
        return () => { swimObs.disconnect(); vertObs.disconnect(); };
    });
</script>

<div class="space-y-12">
    <div class="text-center space-y-2">
        <h2 class="text-3xl font-bold text-transparent bg-clip-text bg-linear-to-r from-indigo-400 to-cyan-400">
            Debate Analysis Timeline
        </h2>
        <p class="text-gray-400 text-sm">Interactive visualization of Transcript + MAST Taxonomy Failures</p>
    </div>

    <!-- View 1: Swimlane -->
    <section>
        <h3 class="text-xl font-semibold text-indigo-300 mb-4 flex items-center gap-2">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
            </svg>
            View 1: Swimlane Overview
        </h3>
        <div
            bind:this={swimlaneContainer}
            class="bg-gray-800 rounded-lg border border-gray-700 overflow-x-auto"
            style="height: 500px; overflow-x: auto; overflow-y: hidden;"
        >
            <svg style="min-width: 100%; display: block;"></svg>
        </div>
        <p class="text-xs text-gray-500 mt-2">Click any card to view the full argument and MAST analysis. Scroll horizontally to see all rounds.</p>
    </section>

    <!-- View 2: Vertical Thread -->
    <section>
        <h3 class="text-xl font-semibold text-indigo-300 mb-4 flex items-center gap-2">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
            View 2: Vertical Thread
        </h3>
        <div
            bind:this={verticalContainer}
            class="bg-gray-800 rounded-lg border border-gray-700 overflow-y-auto relative"
            style="height: 800px;"
        >
            <svg style="width: 100%; display: block;"></svg>

            <!-- Hidden scroll anchors for each vertical node -->
            {#each Object.entries(verticalNodeY) as [key, y]}
                <div
                    id="vthread-{key}"
                    style="position: absolute; top: {y}px; height: 1px; pointer-events: none;"
                ></div>
            {/each}

            <!-- Intervention overlay panel -->
            {#if interventionRound !== null}
                <div
                    style="position: absolute; top: {(roundSepY[interventionRound] ?? 0) + 50}px; left: 50%; transform: translateX(-50%); z-index: 20; width: 420px;"
                    class="bg-gray-900/95 border border-amber-700/60 rounded-lg p-3 space-y-3 shadow-2xl"
                >
                    <div class="flex items-center justify-between">
                        <span class="text-amber-400 font-bold text-sm">⚡ Human Moderator — Round {interventionRound}</span>
                        <button
                            on:click={() => { interventionRound = null; interventionInput = ''; }}
                            class="text-gray-500 hover:text-gray-300 text-xs"
                        >✕ cancel</button>
                    </div>

                    {#if roundAnalyses[interventionRound]?.failures?.filter((f: any) => f.detected).length > 0}
                        <div>
                            <p class="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-1">MAST Failures Detected:</p>
                            <div class="space-y-1">
                                {#each roundAnalyses[interventionRound].failures.filter((f: any) => f.detected) as failure}
                                    <div class="flex items-center gap-2 text-xs bg-red-900/30 border border-red-800/40 rounded px-2 py-1">
                                        <span class="font-black text-red-400">{failure.id}</span>
                                        <span class="text-red-200">{failure.name}</span>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {:else}
                        <p class="text-xs text-green-400 italic">No MAST failures in this round.</p>
                    {/if}

                    <div>
                        <label class="text-xs text-gray-400 font-semibold uppercase tracking-wide block mb-1">
                            Your direction for Round {interventionRound}:
                        </label>
                        <textarea
                            bind:value={interventionInput}
                            class="w-full h-20 bg-gray-800 p-2 border border-gray-600 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 transition resize-none"
                            placeholder="e.g., Focus on concrete evidence, avoid logical fallacies..."
                        ></textarea>
                    </div>

                    <button
                        on:click={handleRegenerateClick}
                        disabled={isRegenerating}
                        class="w-full flex items-center justify-center gap-2 bg-amber-600 hover:bg-amber-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-lg transition text-sm"
                    >
                        {#if isRegenerating}
                            <div class="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                            Regenerating...
                        {:else}
                            ⚡ Regenerate Round {interventionRound}
                        {/if}
                    </button>
                </div>
            {/if}
        </div>
    </section>
</div>

<!-- Modal -->
{#if modalOpen && modalData}
    <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
        on:click={closeModal}
    >
        <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
        <div
            class="bg-gray-800 border border-gray-600 rounded-xl shadow-2xl w-full max-w-3xl p-6 m-4 max-h-[90vh] overflow-y-auto"
            on:click|stopPropagation
        >
            <div class="flex justify-between items-start mb-4">
                <div>
                    <div class="flex items-center gap-3">
                        <span class="text-2xl font-bold" style="color: {getColor(modalData.agent)}">
                            {modalData.agent.replace('_', ' ')}
                        </span>
                        <span class="px-2 py-0.5 rounded text-xs font-mono bg-gray-700 text-gray-300">
                            Round {modalData.round}
                        </span>
                        {#if verticalNodeY[`${modalData.agent}-r${modalData.round}`] !== undefined}
                            <button
                                on:click={jumpToThread}
                                class="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded-lg transition"
                            >
                                ↓ Jump to Thread
                            </button>
                        {/if}
                    </div>
                    <div class="mt-1">
                        {#if modalData.hasFailure}
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-900/50 text-red-300 border border-red-700 uppercase tracking-wide">
                                ⚠ Taxonomy Issues
                            </span>
                        {:else}
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-green-900/50 text-green-300 border border-green-700 uppercase tracking-wide">
                                ✓ Verified Healthy
                            </span>
                        {/if}
                    </div>
                </div>
                <button on:click={closeModal} aria-label="Close" class="text-gray-400 hover:text-white transition-colors">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            <div class="bg-gray-900/50 rounded-lg p-4 mb-6 max-h-80 overflow-y-auto border border-gray-700">
                <p class="text-gray-300 leading-relaxed whitespace-pre-wrap text-base" style="font-family: 'Calibri', sans-serif;">
                    {modalData.content}
                </p>
            </div>

            <div class="border-t border-gray-700 pt-4">
                <h4 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                    MAST Analysis (Round Level)
                </h4>
                {#if modalData.analysis?.failures?.filter((f: any) => f.detected).length > 0}
                    <div class="space-y-2">
                        {#each modalData.analysis.failures.filter((f: any) => f.detected) as failure}
                            <div class="flex items-center gap-3 p-3 bg-red-900/20 border border-red-800/50 rounded-lg">
                                <span class="font-black text-red-400 text-lg">{failure.id}</span>
                                <span class="text-red-100 font-medium text-sm">{failure.name}</span>
                            </div>
                        {/each}
                    </div>
                {:else}
                    <div class="text-gray-500 text-sm italic">Compliance check passed.</div>
                {/if}
                {#if modalData.analysis?.summary}
                    <p class="text-sm text-gray-500 mt-3 italic">{modalData.analysis.summary}</p>
                {/if}
            </div>
        </div>
    </div>
{/if}

<style>
    :global(.v-node:hover rect:first-child) {
        fill: #374151;
    }
    :global(.swimlane-box:hover rect:first-child) {
        fill: #374151;
    }
    :global(.drift-line) {
        stroke-dasharray: 5;
        animation: dash 20s linear infinite;
    }
    @keyframes dash {
        from { stroke-dashoffset: 500; }
        to   { stroke-dashoffset: 0; }
    }
</style>
