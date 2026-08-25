/* tcsBU 1.1 (nightly) (c)  amsantos@fc.up.pt */
"use strict";
$(function () {
    /*
     * the svg variable (holds the <SVG> element in DOM)
     */

    var svg = null;

    /*
     * the 'force-directed layout', 'pie' and 'arc' variables for d3.js
     */

    var force = null;

    /*
     * holder for SVG definitions
     */

    var defs = null;

    /*
     * variables that hold nodes and edges read from a file
     */

    var nodeList = [], edgeList = [], linkList = [];

    /*
     * variables that hold nodes which should be highlighted or labeled
     */
    // labelNode/nameIdNode store per-node visibility overrides.  The toolbar
    // flags provide the default for every node; the Info panel can then adjust
    // one node without creating a second SVG text element.
    var labelNode = {}, nameIdNode = {}, highlightNode = [],
        seqHapFlag = false, nameIdFlag = false, nodeNameId = {},
        nodeTextLayout = {}, distanceFlag = false;
    var highlightLink = [], labelLink = {};
    var defaultGroupColor = 'ffffff';

    var edgeWeightFlag = false;
    // When Edge Weight is enabled, Edge Line Width remains the base stroke.
    // Edges with fewer changes are drawn up to this many times thicker.
    var edgeWeightScale = 2;

    var undoStack = [];

    /*
     * Tracks whether a hapconf file has been loaded and how many columns it had (2 or 3).
     * hapconfLoaded: true after a successful loadHaplotypes call.
     * hapconfColumns: 2 = seq;group format, 3 = seq;group;hapname format.
     */
    var hapconfLoaded = false;
    var hapconfColumns = 0;


    /*
     * variables that determine if clicks delete nodes/links
     */

    var deletelink = false, deletenode = false;

    /*
     * Define some default values for 'force-directed layout' algorithm
     */

    var defaultDistance = 12, defaultGravity = 0.05, defaultCharge = -30, defaultLinkDistance = 1,
        defaultLinkStrength = 1, defaultFriction = 0.95;
    // Keep the current layout values in the page-level closure so NetST can
    // serialize and restore them as part of a reproducible project.
    var lnkdist = defaultLinkDistance;
    var lnkstre = defaultLinkStrength;
    var frict = defaultFriction;
    var chrg = defaultCharge;
    var grav = defaultGravity;

    /*
     * standard radius for true haplogroups with 'frequency' = 1
     */

    var standardRadius = 5;
    var ancestorRadius = 1;
    var outerRadiusCoeff = 1.4;
    var innerRadiusCoeff = 0.7;
    var textOffset = 5;
    var haplotypeFontSize = 13;
    var nameIdFontSize = 13;


    /*
     * Variables for the forced layout algorithm elements
     */
    var minTime = Number.POSITIVE_INFINITY;
    var maxTime = Number.NEGATIVE_INFINITY;


    var link, node, path, subpath, linkText;

    var pie, subPie, sector, sectorOuter, sectorNull, sectorSmall;

    var drag;

    var clickLink, clickNode;
    var activeInfoNode = null, refreshActiveNodeInfo = null;

    /*
     * Default line widths. nodeLineWidth is the stroke around each node circle
     * and edgeLineWidth is the stroke of the links (edges). Both are exposed in
     * the Advanced dialog's "Node and Edge Settings".
     */

    var nodeLineWidth = 0;
    var edgeLineWidth = 1;

    var typeid = 0;

    var styleid = 0;

    /*
     * Flag indicating whether trait data has been loaded.
     * Inner ring is only drawn after traits are added.
     */
    var hasTrait = false;

    /*
     * NetST multi-trait metadata rendering. When a metadata config is loaded
     * (window.loadMetaConfig), each visualized trait is drawn as a concentric
     * ring around the node — the group innermost, then outward — instead of the
     * classic single group pie + continuous outer ring. Standalone tcsBU (no
     * metaconf) keeps the classic rendering, so the sidebar stays usable.
     */
    var hasMeta = false;
    var metaConfig = null;           // {ring_width, traits:[...], nodes:{id:{rings:[...]}}}
    var pendingMetaConfig = null;    // config awaiting the async graph load
    var metaRingRatio = 0.5;
    var metaRingLineWidth = 0.1;
    // Relative widths of non-group rings, ordered from inner to outer.
    // Missing entries use 1, so each ring defaults to nodeRadius * metaRingRatio.
    var metaRingScales = [];
    var metaArc = null;
    /*
     * Default zoom
     */

    var zoom = null;

    /*
     * Legend 0 -off, 1 - on
     */

    var legend = 0;
    var legendMinScale = 0.4;
    var legendMaxScale = 3;

    /*
     * Save File available?
     */

    var filesave = false;

    /*
     * Pattern names. See createPattern() below for rendering details.
     */

    var pattern_names = [{id: 'none'}, {icon: 'icon-circles-1', id: 'circles-1'}, {
        icon: 'icon-circles-2', id: 'circles-2'
    }, {icon: 'icon-lines-1', id: 'lines-1'}, {icon: 'icon-lines-2', id: 'lines-2'}, {
        icon: 'icon-lines-3', id: 'lines-3'
    }, {icon: 'icon-lines-4', id: 'lines-4'}, {icon: 'icon-lines-5', id: 'lines-5'}, {
        icon: 'icon-lines-6', id: 'lines-6'
    }, {icon: 'icon-lines-7', id: 'lines-7'}, {icon: 'icon-lines-8', id: 'lines-8'}, {
        icon: 'icon-cross-1', id: 'cross-1'
    }, {icon: 'icon-cross-2', id: 'cross-2'}, {icon: 'icon-cross-3', id: 'cross-3'}, {
        icon: 'icon-cross-4', id: 'cross-4'
    }];


    /*
     * This function reclassifies (changes the group and color) a given haplotype
     * in the haplotype list (referred by its 'index') and changes the svg graph
     * (if enabled) accordingly. The new and old values of the group should
     * be passed, to update the proportions of the corresponding pie chart
     */

    function classify(index, newgroup, oldgroup) {

        /*
         * Grab the new color from groups' list ('newgroup' is the index of that array).
         * Additionally, grab a pattern if available.
         */
        var newcolor = defaultGroupColor, newpattern = 'none';

        var nc = w2ui.groups.find({recid: newgroup}, true)[0];
        if (typeof nc !== 'undefined' && w2ui.groups.records[nc]) {
            newcolor = w2ui.groups.records[nc].color;
            if (w2ui.groups.records[nc].pattern !== 'none') newpattern = "url(#" + newcolor + w2ui.groups.records[nc].pattern + ")";
        }

        /*
         * Grab the haplogroup of this particular haplotype
         */

        var haplogroup = Number(w2ui.haplotypes.records[index].haplogroup);
        var haplocount = Number(w2ui.haplotypes.records[index].count);
        var haplotimecolor = w2ui.haplotypes.records[index].timecolor;
        var haplotime = w2ui.haplotypes.records[index].time;
        var haplostyle = w2ui.haplotypes.records[index].nodestyle;
        /*
         * Grab the node index from nodeList where id == haplogroup
         */

        var nd = $.map(nodeList, function (e, i) {
            if (e.id === haplogroup) return i;
        })[0];

        if (typeof nd !== 'undefined') {

            /*
             * If a node was found, check if the group of this haplotype is already
             * present in the 'proportions' property of the respective node (ng).
             * Check also the index of the group being changed (og): this is usually
             * the default group, but may be any other groups that's being changed.
             */

            var ng = $.map(nodeList[nd].proportions, function (e, i) {
                if (e.group === newgroup) return i;
            })[0];
            var og = $.map(nodeList[nd].proportions, function (e, i) {
                if (e.group === oldgroup) return i;
            })[0];

            /*
             * If ng is undefined, it means that the haplogroup has no elements classified
             * as 'newgroup'. Add this new group to 'proportions' property, with a value
             * of 1, and remove one element from the value of the old group. If both ng and
             * og are defined, increment the proportions' value of ng and decrement the
             * value of og.
             */

            if (typeof og !== 'undefined') {
                if (typeof ng !== 'undefined') {
                    nodeList[nd].proportions[ng].value += haplocount;
                    nodeList[nd].proportions[ng].color = '#' + newcolor;
                    nodeList[nd].proportions[ng].pattern = newpattern;
                    // nodeList[nd].proportions[ng].timecolor = haplotimecolor;
                    // nodeList[nd].proportions[ng].time = haplotime;
                    nodeList[nd].proportions[ng].nodestyle = haplostyle;
                    nodeList[nd].proportions[og].value -= haplocount;
                } else {
                    nodeList[nd].proportions.push({
                        color: '#' + newcolor,
                        group: newgroup,
                        radius: nodeList[nd].radius,
                        value: haplocount,
                        pattern: newpattern,
                        nodestyle: haplostyle,
                    });
                    nodeList[nd].proportions[og].value -= haplocount;
                }

                let timeProportion = nodeList[nd].timeProportions.find(tp => tp.time === haplotime);
                if (timeProportion) {
                    timeProportion.value += haplocount;
                    // timeProportion.timecolor = haplotimecolor;
                } else {
                    nodeList[nd].timeProportions.push({
                        time: haplotime,
                        value: haplocount,
                        timecolor: haplotimecolor,
                        patter: newpattern,
                        radius: nodeList[nd].radius,
                    });
                }
                nodeList[nd].timeProportions.sort(function (a, b) {
                    return Number(a.time) - Number(b.time);
                });


                /*
                 * Find the target svg element (node). If it exists, apply changes
                 */

                if (svg && !hasMeta) {
                    var n = svg.selectAll('.node')
                    path = n.selectAll('.outer-path').data(function (d) {
                        return pie(d.proportions);
                    });


                    path.enter()
                        .append('path')
                        .attr('class', 'outer-path')
                        .attr('d', function (d) {
                            if (isInnerNode(d) || !hasTrait) {
                                return sector(d)
                            } else {
                                if (styleid === 1) return sector(d); else if (styleid === 2) return sectorNull(d); else return sectorOuter(d);
                            }
                        })
                        .style('fill', function (d) {
                            if (d.data.pattern === 'none') return d.data.color; else return d.data.pattern;
                        });
                    path.style('stroke-width', '0').style('stroke', 'none');

                    subpath = n.selectAll('.subpath').data(function (d) {
                        return subPie(d.timeProportions);
                    });

                    subpath.enter()
                        .append('path')
                        .attr('class', "subpath")
                        .attr('d', function (d) {
                            if (isInnerNode(d) || !hasTrait) {
                                return sectorNull(d);
                            } else {
                                if (styleid === 1) return sectorNull(d); else if (styleid === 2) return sector(d); else return sectorSmall(d);
                            }
                        })
                        .style('fill', function (d) {
                            return tcGradient(d.data.timecolor, typeid);
                        });


                    /*
                     * These two commands may be used to implement
                     * a stroke between arcs in the pie
                     * .style('stroke-width', '0')
                     * .style('stroke', 'none');
                     */
                    subpath.style('stroke-width', '0').style('stroke', 'none');
                    path.exit().remove();
                    subpath.exit().remove();

                    force.nodes(nodeList).links(linkList).start();
                }

            } else {
                w2alert('Serious error!', 'ERROR');
            }
        }


    }

    /*
     * Create an SVG pattern definition and append it to the SVG <defs> element
     * so it can be referenced as a fill URL (e.g. "url(#<color><pat>)").
     * 'pat' is the pattern name, 'col' is the hex color string (without '#').
     */

    function createPattern(pat, col) {
        if (pat === 'none') return;
        var name = col + pat;
        var p = defs.append("pattern");
        p.attr("id", name)
            .attr("patternUnits", "userSpaceOnUse")
            .attr("width", 10)
            .attr("height", 10);

        /*
         * Append a rect that will hold the background color
         */

        p.append("rect")
            .attr("width", "10")
            .attr("height", "10")
            .attr("x", "0")
            .attr("y", "0")
            .attr("fill", "#" + col)
            .attr("stroke-width", "0");

        switch (pat) {
            case 'lines-1':
                p.append('path')
                    .attr('d', 'M3,0 V10 M8,0 V10')
                    .attr('stroke', '#000000')
                    .attr('stroke-width', 0.5);
                break;
            case 'lines-2':
                p.append('path')
                    .attr('d', 'M3,0 V10 M8,0 V10')
                    .attr('stroke', '#000000')
                    .attr('stroke-width', 1.5);
                break;
            case 'lines-3':
                p.append('path')
                    .attr('d', 'M0,3 H10 M0,8 H10')
                    .attr('stroke', '#000000')
                    .attr('stroke-width', 0.5);
                break;
            case 'lines-4':
                p.append('path')
                    .attr('d', 'M0,3 H10 M0,8 H10')
                    .attr('stroke', '#000000')
                    .attr('stroke-width', 1.5);
                break;
            case 'lines-5':
                p.append('path')
                    .attr('d', 'M4,-1 l10,10 M-1,4 l10,10')
                    .attr('stroke', '#000000')
                    .attr('stroke-width', 0.5);
                break;
            case 'lines-6':
                p.append('path')
                    .attr('d', 'M4,-1 l10,10 M-1,4 l10,10')
                    .attr('stroke', '#000000')
                    .attr('stroke-width', 1.5);
                break;
            case 'lines-7':
                p.append('path')
                    .attr('d', 'M4,-1 l-10,10 M2,11 l10,-10')
                    .attr('stroke', '#000000')
                    .attr('stroke-width', 0.5);
                break;
            case 'lines-8':
                p.append('path')
                    .attr('d', 'M4,-1 l-10,10 M2,11 l10,-10')
                    .attr('stroke', '#000000')
                    .attr('stroke-width', 1.5);
                break;
            case 'cross-1':
                p.append('path')
                    .attr('d', 'M3,0 V10 M8,0 V10 M0,3 H10 M0,8 H10')
                    .attr('stroke', '#000000')
                    .attr('stroke-width', 0.5);
                break;
            case 'cross-2':
                p.append('path')
                    .attr('d', 'M3,0 V10 M8,0 V10 M0,3 H10 M0,8 H10')
                    .attr('stroke', '#000000')
                    .attr('stroke-width', 1.5);
                break;
            case 'cross-3':
                p.append('path')
                    .attr('d', 'M0,0 L10,10 M10,0 L0,10')
                    .attr('stroke', '#000000')
                    .attr('stroke-width', 0.5);
                break;
            case 'cross-4':
                p.append('path')
                    .attr('d', 'M0,0 L10,10 M10,0 L0,10')
                    .attr('stroke', '#000000')
                    .attr('stroke-width', 1.5);
                break;
            case 'circles-1':
                p.append("rect").attr({width: "10", height: "10", fill: "#" + col});
                p.append("circle")
                    .attr({cx: 2, cy: 2, r: 1, transform: "translate(0,0)", fill: "#000000"});
                p.append("circle")
                    .attr({cx: 2, cy: 7, r: 1, transform: "translate(0,0)", fill: "#000000"});
                p.append("circle")
                    .attr({cx: 7, cy: 2, r: 1, transform: "translate(0,0)", fill: "#000000"});
                p.append("circle")
                    .attr({cx: 7, cy: 7, r: 1, transform: "translate(0,0)", fill: "#000000"});
                break;
            case 'circles-2':
                p.append("rect").attr({width: "10", height: "10", fill: "#" + col});
                p.append("circle")
                    .attr({cx: 5, cy: 5, r: 3, transform: "translate(0,0)", fill: "#000000"})
                break;
        }
    }

    function isInnerNode(d) {
        return d.data.nodestyle === 0;
    }

    /**
     * Map a timecolor hex string (range "08"–"f7") to a gradient color.
     * t=0 → low endpoint, t=1 → high endpoint.
     * mode: 0=gray, 1=red, 2=green, 3=blue
     */
    function tcGradient(tc, mode) {
        var v = parseInt(tc, 16);
        var t = (v - 8) / 239;
        var r, g, b;
        var h = function (n) {
            return ('0' + Math.round(n).toString(16)).slice(-2);
        };
        if (mode === 0) {
            // Default continuous scale: gray (#BDBDBD) → black (#000000).
            r = g = b = 189 * (1 - t);
        } else if (mode === 1) {
            r = 155 + 100 * t;
            g = 28 + 137 * t;
            b = 28 + 137 * t;
        }   // crimson → coral
        else if (mode === 2) {
            r = 22 + 112 * t;
            g = 101 + 138 * t;
            b = 52 + 120 * t;
        }  // forest → mint
        else if (mode === 3) {
            r = 30 + 117 * t;
            g = 58 + 139 * t;
            b = 138 + 115 * t;
        }  // navy → sky
        return '#' + h(r) + h(g) + h(b);
    }

    function openAdvancedSettings() {
        $('#advNodeRadius').val(standardRadius);
        $('#advNodeLineWidth').val(nodeLineWidth);
        $('#advEdgeLineWidth').val(edgeLineWidth);
        $('#advEdgeWeightScale').val(edgeWeightScale);
        $('#advMetaRingLineWidth').val(metaRingLineWidth);
        $('#advTextOffset').val(textOffset);
        $('#advHaplotypeFontSize').val(haplotypeFontSize);
        $('#advNameIdFontSize').val(nameIdFontSize);
        $('#advMetaRingRatio').val(metaRingRatio);
        $('#advMetaRingScales').val(metaRingScales.join(', '));
        var ringNames = [];
        if (metaConfig && metaConfig.traits) {
            ringNames = metaConfig.traits.filter(function (trait) {
                return !trait.group;
            }).map(function (trait) {
                return trait.name;
            });
        }
        $('#advMetaRingOrder').text(ringNames.length
            ? 'Current order: ' + ringNames.join(' \u2192 ')
            : 'No outer metadata rings are currently loaded.');
        $('#adv-layout-error').hide();
        var overlay = $('#advanced-settings-overlay');
        overlay.toggle();
    }

    /*
     * NetST metadata rings.
     *
     * loadMetaConfig receives a config precomputed by NetST: for each GML node
     * id, a list of rings (group first, then outward). A discrete ring carries
     * segments {value, color}; a continuous ring carries a single solid color.
     * The per-node ring geometry is derived at draw time so it tracks the
     * frequency-scaled node radius and the current ring width.
     */
    function loadMetaConfig(config) {
        if (!config || !config.nodes) return;
        // The graph loads asynchronously (FileReader). If it is not parsed yet,
        // remember the config and apply it once loadGraph finishes.
        pendingMetaConfig = config;
        if (nodeList && nodeList.length > 0) applyMetaConfig();
    }

    function applyMetaConfig() {
        var config = pendingMetaConfig;
        if (!config || !config.nodes) return;
        metaConfig = config;
        if (typeof config.ring_ratio === 'number' && config.ring_ratio > 0) {
            metaRingRatio = config.ring_ratio;
        } else if (typeof config.ring_width === 'number' && config.ring_width > 0) {
            metaRingRatio = config.ring_width / standardRadius;
        }
        for (var i = 0; i < nodeList.length; i++) {
            var entry = config.nodes[nodeList[i].id];
            nodeList[i].metaRings = (entry && entry.rings) ? entry.rings : [];
        }
        hasMeta = true;
        hasTrait = true;
        pendingMetaConfig = null;
        populateMetaGroupsFromConfig();
        if (svg) updateSVG();
    }

    function metaTraitByName(name) {
        if (!metaConfig || !metaConfig.traits) return null;
        for (var i = 0; i < metaConfig.traits.length; i++) {
            if (metaConfig.traits[i].name === name) return metaConfig.traits[i];
        }
        return null;
    }

    function metaGroupTrait() {
        if (!metaConfig || !metaConfig.traits) return null;
        for (var i = 0; i < metaConfig.traits.length; i++) {
            if (metaConfig.traits[i].group) return metaConfig.traits[i];
        }
        return null;
    }

    function normalizedMetaColor(color, fallback) {
        var text = String(color || '').trim();
        if (text[0] !== '#') text = '#' + text;
        if (/^#[0-9a-f]{3}$/i.test(text)) {
            text = '#' + text[1] + text[1] + text[2] + text[2] + text[3] + text[3];
        }
        return /^#[0-9a-f]{6}$/i.test(text) ? text.toUpperCase() : (fallback || '#DDDDDD');
    }

    function metaHashColor(label) {
        var hash = 0;
        var text = String(label || '');
        for (var i = 0; i < text.length; i++) {
            hash = ((hash * 131) + text.charCodeAt(i)) & 0xFFFFFF;
        }
        return '#' + ((hash | 0x202020) >>> 0).toString(16).slice(-6).padStart(6, '0').toUpperCase();
    }

    function metaCategoryColor(trait, label) {
        var categories = trait.categories || (trait.categories = []);
        for (var i = 0; i < categories.length; i++) {
            if (String(categories[i].label) === String(label)) {
                return normalizedMetaColor(categories[i].color, '#DDDDDD');
            }
        }
        var color = String(label) === 'Default'
            ? '#' + defaultGroupColor : metaHashColor(label);
        if (label !== '') categories.push({label: label, color: color});
        return color;
    }

    function metaLerpColor(low, high, fraction) {
        function rgb(value, fallback) {
            var text = normalizedMetaColor(value, fallback).substr(1);
            return [
                parseInt(text.substr(0, 2), 16),
                parseInt(text.substr(2, 2), 16),
                parseInt(text.substr(4, 2), 16)
            ];
        }

        var lo = rgb(low, '#BDBDBD');
        var hi = rgb(high, '#000000');
        var t = Math.max(0, Math.min(1, Number(fraction)));

        function channel(index) {
            return Math.round(lo[index] + (hi[index] - lo[index]) * t)
                .toString(16).padStart(2, '0');
        }

        return ('#' + channel(0) + channel(1) + channel(2)).toUpperCase();
    }

    function refreshMetaLegend() {
        if (legend !== 1) return;
        $('.legend').remove();
        d3.selectAll('.meta-legend-gradient').remove();
        legend = 0;
        insertLegend();
    }

    function rebuildMetaTraitRings(traitName, redraw) {
        if (!hasMeta || !metaConfig || !metaConfig.sample_values) return;
        var trait = metaTraitByName(traitName);
        if (!trait) return;
        var numeric = trait.kind === 'continuous';
        var low = numeric && trait.gradient ? trait.gradient[0] : '#BDBDBD';
        var high = numeric && trait.gradient ? trait.gradient[1] : '#000000';
        var vmin = Number(trait.vmin);
        var vmax = Number(trait.vmax);
        if (!isFinite(vmin)) vmin = 0;
        if (!isFinite(vmax)) vmax = 1;
        var span = vmax - vmin;

        nodeList.forEach(function (node) {
            if (!node.metaRings || node.nodestyle !== 1) return;
            var ring = null;
            for (var r = 0; r < node.metaRings.length; r++) {
                if (node.metaRings[r].trait === traitName) {
                    ring = node.metaRings[r];
                    break;
                }
            }
            if (!ring) return;
            var samples = String(node.name || '').split('\n').filter(function (sample) {
                return sample.trim() !== '';
            });
            var counts = {};
            var order = [];
            var missing = 0;
            samples.forEach(function (sample) {
                var row = metaConfig.sample_values[sample.trim()] || {};
                var raw = row[traitName];
                if (raw === undefined || String(raw).trim() === '') {
                    missing += 1;
                    return;
                }
                var value = numeric ? Number(raw) : String(raw).trim();
                if (numeric && !isFinite(value)) {
                    missing += 1;
                    return;
                }
                var key = String(value);
                if (!Object.prototype.hasOwnProperty.call(counts, key)) {
                    counts[key] = {value: value, count: 0};
                    order.push(key);
                }
                counts[key].count += 1;
            });

            var segments = [];
            if (numeric) {
                var weighted = 0;
                var validCount = 0;
                order.sort(function (a, b) {
                    return counts[a].value - counts[b].value;
                });
                order.forEach(function (key) {
                    var item = counts[key];
                    var fraction = span === 0 ? 0.5 : (item.value - vmin) / span;
                    segments.push({
                        label: item.value,
                        value: item.count,
                        color: metaLerpColor(low, high, fraction)
                    });
                    weighted += item.value * item.count;
                    validCount += item.count;
                });
                if (missing) segments.push({label: '', value: missing, color: '#FFFFFF'});
                if (!segments.length) segments.push({label: '', value: 1, color: '#FFFFFF'});
                ring.value = validCount ? weighted / validCount : null;
                ring.color = validCount
                    ? metaLerpColor(low, high, span === 0 ? 0.5 : (ring.value - vmin) / span)
                    : '#FFFFFF';
            } else {
                var categoryOrder = [];
                (trait.categories || []).forEach(function (entry) {
                    var key = String(entry.label);
                    if (Object.prototype.hasOwnProperty.call(counts, key)) categoryOrder.push(key);
                });
                order.forEach(function (key) {
                    if (categoryOrder.indexOf(key) < 0) categoryOrder.push(key);
                });
                categoryOrder.forEach(function (key) {
                    segments.push({
                        label: counts[key].value,
                        value: counts[key].count,
                        color: metaCategoryColor(trait, counts[key].value)
                    });
                });
                if (missing) segments.push({
                    label: trait.group ? 'Default' : '',
                    value: missing,
                    color: trait.group
                        ? metaCategoryColor(trait, 'Default') : '#DDDDDD'
                });
                if (!segments.length) segments.push({
                    label: trait.group ? 'Default' : '',
                    value: 1,
                    color: trait.group
                        ? metaCategoryColor(trait, 'Default') : '#DDDDDD'
                });
            }
            ring.segments = segments;
        });
        if (redraw !== false && svg) {
            updateSVG();
            refreshMetaLegend();
        }
    }

    function populateMetaGroupsFromConfig() {
        if (!metaConfig || !metaConfig.traits) return;
        var groupTrait = metaGroupTrait();
        if (groupTrait && w2ui.groups) {
            var groups = [{recid: 'Default', color: defaultGroupColor, pattern: 'none'}];
            (groupTrait.categories || []).forEach(function (entry) {
                var label = String(entry.label || '').trim();
                if (!label || label === 'Default') return;
                groups.push({
                    recid: label,
                    color: normalizedMetaColor(entry.color, '#DDDDDD').substr(1),
                    pattern: 'none'
                });
            });
            w2ui.groups.clear();
            w2ui.groups.add(groups);
            w2ui.groups.refresh();
        }
    }

    function syncMetaGroupColor(groupName, color) {
        var trait = metaGroupTrait();
        if (!trait) return;
        var normalized = normalizedMetaColor(color, '#DDDDDD');
        var found = false;
        (trait.categories || []).forEach(function (entry) {
            if (String(entry.label) === String(groupName)) {
                entry.color = normalized;
                found = true;
            }
        });
        if (!found) {
            (trait.categories || (trait.categories = [])).push({
                label: groupName, color: normalized
            });
        }
        rebuildMetaTraitRings(trait.name);
    }

    function syncMetaGroupName(oldName, newName) {
        var trait = metaGroupTrait();
        if (!trait || oldName === newName) return;
        (trait.categories || []).forEach(function (entry) {
            if (String(entry.label) === String(oldName)) entry.label = newName;
        });
        var values = metaConfig.sample_values || {};
        Object.keys(values).forEach(function (sample) {
            if (String(values[sample][trait.name]) === String(oldName)) {
                values[sample][trait.name] = newName;
            }
        });
        rebuildMetaTraitRings(trait.name);
    }

    function syncMetaHaplotypeGroup(sample, group) {
        var trait = metaGroupTrait();
        if (!trait || !metaConfig.sample_values) return;
        if (!metaConfig.sample_values[sample]) metaConfig.sample_values[sample] = {};
        metaConfig.sample_values[sample][trait.name] = group;
        rebuildMetaTraitRings(trait.name);
    }

    function syncAllMetaHaplotypeGroups(redraw) {
        var trait = metaGroupTrait();
        if (!trait || !metaConfig || !metaConfig.sample_values || !w2ui.haplotypes) return;
        w2ui.haplotypes.records.forEach(function (record) {
            if (!metaConfig.sample_values[record.recid]) {
                metaConfig.sample_values[record.recid] = {};
            }
            metaConfig.sample_values[record.recid][trait.name] =
                record.group || 'Default';
        });
        rebuildMetaTraitRings(trait.name, redraw);
    }

    function computeMetaSegments(d) {
        var rings = d.metaRings;
        if (d.nodestyle === 0 || !rings || rings.length === 0) {
            d.metaOuterRadius = d.radius;
            return [];
        }
        var segments = [];
        var base = d.radius;
        var ringWidth = base * metaRingRatio;
        var currentOuter = base;
        for (var k = 0; k < rings.length; k++) {
            var ring = rings[k] || {};
            var parts = ring.segments || [];
            if (k > 0) {
                var allMissing = parts.length > 0 && parts.every(function (p) {
                    return p.label === '' || p.label === undefined || p.label === null;
                });
                if (allMissing) continue;
            }
            var inner = 0;
            var outer = base;
            if (k > 0) {
                var scale = Number(metaRingScales[k - 1]);
                if (!isFinite(scale) || scale <= 0) scale = 1;
                inner = currentOuter;
                outer = inner + ringWidth * scale;
                currentOuter = outer;
            }
            var ringKind = ring.kind || 'categorical';
            if (ring.kind === 'continuous' && parts.length === 0) {
                segments.push({
                    inner: inner, outer: outer, startAngle: 0,
                    endAngle: 2 * Math.PI, color: ring.color || '#ffffff',
                    kind: ringKind,
                });
                continue;
            }
            var total = 0;
            for (var s = 0; s < parts.length; s++) total += (parts[s].value || 0);
            if (total <= 0) {
                segments.push({
                    inner: inner, outer: outer, startAngle: 0,
                    endAngle: 2 * Math.PI, color: '#ffffff',
                    kind: ringKind,
                });
                continue;
            }
            var angle = 0;
            for (var p = 0; p < parts.length; p++) {
                var frac = (parts[p].value || 0) / total;
                var start = angle;
                var end = angle + frac * 2 * Math.PI;
                segments.push({
                    inner: inner, outer: outer, startAngle: start,
                    endAngle: end, color: parts[p].color || '#ffffff',
                    kind: ringKind,
                });
                angle = end;
            }
        }
        d.metaOuterRadius = currentOuter;
        return segments;
    }

    function renderedNodeRadius(d) {
        if (hasMeta) return d.metaOuterRadius || d.radius;
        if (d.nodestyle === 1 && hasTrait && styleid !== 1 && styleid !== 2) {
            return d.radius * outerRadiusCoeff;
        }
        return d.radius;
    }

    /*
     * McAN/RMST writes Changes as a scalar graph distance (for example "2").
     * Older GML producers may instead write a list of mutation tokens, so keep
     * a small compatibility fallback that counts those tokens.
     */
    function edgeChangeValue(changes) {
        if (typeof changes === 'number') {
            return isFinite(changes) ? Math.max(0, changes) : 0;
        }
        var text = $.trim(String(changes === undefined || changes === null ? '' : changes));
        if (text === '') return 0;
        var scalar = Number(text);
        if (isFinite(scalar)) return Math.max(0, scalar);
        var tokens = text.split(/[\s,;]+/).filter(function (token) {
            return token !== '';
        });
        return tokens.length;
    }

    function edgeWeightLevels() {
        var levels = linkList.map(function (edge) {
            return edgeChangeValue(edge.changes);
        }).filter(function (value, index, values) {
            return values.indexOf(value) === index;
        });
        levels.sort(function (a, b) {
            return a - b;
        });
        return levels;
    }

    function edgeWeightStrokeWidth(edge, levels) {
        var changes = edgeChangeValue(edge ? edge.changes : 0);
        var levelIndex = levels.indexOf(changes);
        if (levelIndex < 0) levelIndex = levels.length - 1;
        // Spread the distinct Changes levels across the complete width range.
        // The curve deliberately increases contrast between adjacent levels.
        var normalized = levels.length > 1 ? levelIndex / (levels.length - 1) : 0;
        var emphasis = Math.pow(1 - normalized, 1.5);
        var multiplier = 1 + (edgeWeightScale - 1) * emphasis;
        return edgeLineWidth * multiplier;
    }

    function drawMetaRings(nodeSelection) {
        var metapath = nodeSelection.selectAll('.meta-path').remove();
        metapath = nodeSelection.selectAll('.meta-path').data(function (d) {
            return d.metaSegments || [];
        });
        metapath.enter()
            .append('path')
            .attr('class', 'meta-path')
            .attr('d', function (d) {
                return metaArc(d);
            })
            .style('fill', function (d) {
                return d.color;
            });
        metapath
            .style('stroke-width', function (d) {
                if (d.kind === 'continuous') return Math.max(metaRingLineWidth * 0.3, 0.1);
                return metaRingLineWidth;
            })
            .style('stroke', function (d) {
                if (d.kind === 'continuous') return metaRingLineWidth > 0 ? '#666666' : 'none';
                return metaRingLineWidth > 0 ? '#000000' : 'none';
            });
        metapath.exit().remove();
    }

    function hasOwn(object, key) {
        return Object.prototype.hasOwnProperty.call(object, key);
    }

    function nodeLabelKey(node) {
        return String(node.id);
    }

    function isIntermediateNode(node) {
        if (!node) return false;
        var nameIds = String(node.name || '').split('\n').filter(function (value) {
            return value.trim() !== '';
        });
        var firstNameId = nameIds.length > 0 ? nameIds[0].trim() : '';
        if (!/^IN/.test(firstNameId)) return false;

        var activeGroups = (node.proportions || []).filter(function (proportion) {
            return Number(proportion.value) > 0;
        });
        return activeGroups.length > 0 && activeGroups.every(function (proportion) {
            return proportion.group === 'Default';
        });
    }

    function getHaplotypeLabel(node) {
        var haploNodes = nodeList.filter(function (item) {
            return item.nodestyle === 1 && !isIntermediateNode(item);
        });
        var index = haploNodes.indexOf(node);
        return index >= 0 ? 'H' + (index + 1) : null;
    }

    function getNodeDisplayLabel(node) {
        if (node.nodestyle !== 1 || isIntermediateNode(node)) return 'Transition';
        if (hapconfColumns === 3 && node.hap) return node.hap;
        var names = node.name ? node.name.split('\n').filter(function (name) {
            return name.trim() !== '';
        }) : [];
        return names.length > 0 ? names[0] : getHaplotypeLabel(node);
    }

    function isNodeTextVisible(node, type) {
        // A generated intermediate is identified by an IN-prefixed Name/ID
        // while all of its active members remain in Default. Toolbar-wide
        // toggles and stale overrides must never expose text for such nodes.
        if (!node || node.nodestyle !== 1 || isIntermediateNode(node)) return false;
        var overrides = type === 'haplotype' ? labelNode : nameIdNode;
        var globalFlag = type === 'haplotype' ? seqHapFlag : nameIdFlag;
        return hasOwn(overrides, node.name) ? overrides[node.name] : globalFlag;
    }

    /*
     * Text coordinates are stored as pixel offsets from the corresponding
     * node's circle centre.  Keeping haplotype and Name/ID settings separate
     * lets both labels retain independent positions through graph redraws and
     * force-layout movement.
     */
    function getNodeTextLayout(node, type) {
        var key = nodeLabelKey(node);
        var stored = nodeTextLayout[key] && nodeTextLayout[key][type];
        var defaults = {
            x: textOffset + renderedNodeRadius(node),
            y: type === 'haplotype' ? 4 : 5,
            size: type === 'haplotype' ? haplotypeFontSize : nameIdFontSize
        };
        return {
            x: stored && isFinite(stored.x) ? stored.x : defaults.x,
            y: stored && isFinite(stored.y) ? stored.y : defaults.y,
            size: stored && isFinite(stored.size) ? stored.size : defaults.size
        };
    }

    function setNodeTextLayout(node, type, values) {
        var key = nodeLabelKey(node);
        if (!nodeTextLayout[key]) nodeTextLayout[key] = {};
        nodeTextLayout[key][type] = {
            x: Number(values.x),
            y: Number(values.y),
            size: Number(values.size)
        };
    }

    function applyGlobalNodeFontSize(type, size) {
        Object.keys(nodeTextLayout).forEach(function (key) {
            if (nodeTextLayout[key] && nodeTextLayout[key][type]) {
                nodeTextLayout[key][type].size = size;
            }
        });
    }

    function renderNodeTextLabels() {
        node.each(function (datum) {
            if (datum.nodestyle !== 1 || isIntermediateNode(datum)) return;
            var parent = d3.select(this);
            var labels = [{
                type: 'haplotype',
                className: 'node_hap',
                text: getNodeDisplayLabel(datum)
            }, {
                type: 'nameId',
                className: 'node_name_id',
                text: getNodeNameIdLabel(datum)
            }];

            labels.forEach(function (label) {
                if (!label.text || !isNodeTextVisible(datum, label.type)) return;
                var layout = getNodeTextLayout(datum, label.type);
                parent.append('text')
                    .attr('class', 'node-label ' + label.className)
                    .attr('data-label-type', label.type)
                    .attr('dx', layout.x)
                    .attr('dy', layout.y)
                    .text(label.text)
                    .style('font-family', 'Times New Roman')
                    .style('stroke-width', '0.2px')
                    .style('font-size', layout.size + 'px')
                    .style('pointer-events', 'none');
            });
        });
    }

    /*
     * Paint the current force-layout coordinates immediately.
     *
     * Normally D3 does this from the asynchronous "tick" callback.  Project
     * restore is different: updateSVG() rebuilds every SVG element and starts
     * the force, then applyProjectViewState() stops it straight away so the
     * saved coordinates are not changed.  Without a synchronous paint, that
     * first tick never runs and all newly-created nodes remain at the SVG
     * origin.  Keep the coordinate painting in one function so both paths use
     * exactly the same rendering logic.
     */
    function updateSVGPositions() {
        if (!svg) return;

        if (link) {
            link.attr("x1", function (d) {
                return d.source.x;
            })
                .attr("y1", function (d) {
                    return d.source.y;
                })
                .attr("x2", function (d) {
                    return d.target.x;
                })
                .attr("y2", function (d) {
                    return d.target.y;
                });
        }

        if (distanceFlag && linkText) {
            linkText
                .attr('x', function (d) {
                    return (d.source.x + d.target.x) / 2;
                })
                .attr('y', function (d) {
                    return (d.source.y + d.target.y) / 2;
                });
        }

        Object.keys(labelLink).forEach(function (lid) {
            var ldata = linkList.find(function (l) {
                return l.id === lid;
            });
            if (!ldata) return;
            var linkEl = svg.select('#' + lid);
            if (!linkEl.empty()) {
                svg.select('.link-label-info[data-lid="' + lid + '"]')
                    .attr('x', (ldata.source.x + ldata.target.x) / 2)
                    .attr('y', (ldata.source.y + ldata.target.y) / 2);
            }
        });

        if (node) {
            node.attr("x", function (d) {
                return d.x;
            })
                .attr("y", function (d) {
                    return d.y;
                })
                .attr("transform", function (d) {
                    return "translate(" + d.x + "," + d.y + ")";
                });
        }
    }

    function updateSVG() {
        svg.selectAll('.link-label-info').remove();
        link = svg.selectAll('.link').remove();
        link = svg.selectAll('.link').data(linkList);
        link.enter().append('line')
            .attr('class', 'link')
            .attr('id', function (d) {
                return d.id;
            })
            .on('click', clickLink);
        var weightLevels = edgeWeightFlag ? edgeWeightLevels() : [];
        if (edgeWeightFlag) {
            link.style('stroke-width', function (d) {
                return edgeWeightStrokeWidth(d, weightLevels);
            })
                .style('stroke', '#000000');
        } else {
            link.style('stroke-width', edgeLineWidth).style('stroke', '#000000');
        }
        link.exit().remove();

        // Apply link highlight and per-link changes labels.
        highlightLink.forEach(function (lid) {
            svg.select('#' + lid)
                .style('stroke', '#FF0000')
                .style('stroke-width', function (d) {
                    return (edgeWeightFlag ? edgeWeightStrokeWidth(d, weightLevels) : edgeLineWidth) * 3;
                });
        });
        Object.keys(labelLink).forEach(function (lid) {
            var ldata = linkList.find(function (l) {
                return l.id === lid;
            });
            if (!ldata) return;
            svg.select('#' + lid)
                .each(function () {
                    var el = d3.select(this.parentNode);
                    el.append('text')
                        .attr('class', 'link-label-info')
                        .attr('data-lid', lid)
                        .attr('x', function () {
                            return (ldata.source.x + ldata.target.x) / 2;
                        })
                        .attr('y', function () {
                            return (ldata.source.y + ldata.target.y) / 2;
                        })
                        .attr('text-anchor', 'middle')
                        .attr('dy', '-4px')
                        .text(labelLink[lid])
                        .style('font-family', 'Times New Roman')
                        .style('stroke-width', '0.2px')
                        .style('font-size', '11px')
                        .style('fill', '#c00');
                });
        });

        if (hasMeta) {
            for (var mi = 0; mi < nodeList.length; mi++) {
                nodeList[mi].metaSegments = computeMetaSegments(nodeList[mi]);
            }
        }

        node = svg.selectAll('.node').remove();
        node = svg.selectAll('.node').data(nodeList);
        node.enter().append('g')
            .attr('class', 'node')
            .attr('id', function (d) {
                return d.name;
            })
            .on('click', clickNode)
            .call(drag)
            .append('circle')
            .attr('class', 'node-circle')
            .attr('r', function (d) {
                return renderedNodeRadius(d);
            });

        node.style('stroke-width', function () {
            return nodeLineWidth;
        }).style('stroke', '#000000').style('fill', '#000000');
        node.exit().remove();


        if (hasMeta) {
            // NetST multi-trait rings replace the classic group pie + outer ring.
            drawMetaRings(node);
        } else {
            // Draw the outer-ring pie sectors (primary group coloring)
            path = node.selectAll('.outer-path').remove();
            path = node.selectAll('.outer-path').data(function (d) {
                return pie(d.proportions);
            });

            path.enter()
                .append('path')
                .attr('class', "outer-path")
                .attr('d', function (d) {
                    if (isInnerNode(d) || !hasTrait) {
                        return sector(d)
                    } else {
                        if (styleid === 1) return sector(d); else if (styleid === 2) return sectorNull(d); else return sectorOuter(d);
                    }
                })
                .style('fill', function (d) {
                    if (d.data.pattern === 'none') return d.data.color; else return d.data.pattern;
                });
            path.style('stroke-width', '0').style('stroke', 'none');
            path.exit().remove();

            // Draw the inner sub-ring pie sectors (time/continuous trait coloring)
            subpath = node.selectAll('.subpath').remove();
            subpath = node.selectAll('.subpath').data(function (d) {
                return subPie(d.timeProportions);
            });

            subpath.enter()
                .append('path')
                .attr('class', 'subpath')
                .attr('d', function (d) {
                    if (isInnerNode(d) || !hasTrait) {
                        return sectorNull(d);
                    } else {
                        if (styleid === 1) return sectorNull(d); else if (styleid === 2) return sector(d); else return sectorSmall(d);
                    }
                })
                .style('fill', function (d) {
                    return tcGradient(d.data.timecolor, typeid);
                });

            /*
             * These two commands may be used to implement
             * a stroke between arcs in the pie
             * .style('stroke-width', '0')
             * .style('stroke', 'none');
             */
            subpath.style('stroke-width', '0').style('stroke', 'none');

            subpath.exit().remove();
        }

        linkText = svg.selectAll(".link-text").remove();
        if (distanceFlag) {
            linkText = svg.selectAll('.link-text').data(linkList);
            linkText.enter().append('text')
                .attr('class', 'link-text')
                .attr('text-anchor', 'middle')
                .text(function (d) {
                    return d.changes;
                })
                .style('font-family', 'Times New Roman') // Set the font family
                .style("stroke-width", '0.2px')
                .style('font-size', '13px');
            linkText.exit().remove();
        }

        force.nodes(nodeList).links(linkList).start();
        // Do not wait for the first asynchronous force tick before displaying
        // the current coordinates.  This is required when restoring a saved
        // project layout, because the force is intentionally stopped at once.
        updateSVGPositions();

        // Apply node highlight and the unified per-node text decorations.
        highlightNode.forEach(function (name) {
            // Build a CSS selector, escaping any newline characters in the node name.
            var selector = '#' + name.replaceAll("\n", "\\a ");
            d3.select(selector).select(".node-circle").style({'stroke': '#FF0000', 'stroke-width': Math.max(nodeLineWidth, 1) * 3});
        });
        renderNodeTextLabels();
    }

    /*
     * The group's grid
     */

    function getGroupsGrid() {

        /*
         * Append an <input> element at the end of the body. This will serve as an anchor to be used
         * by button 'loadGroups' to browse files for reading a group's file (csv delimited text
         * file with two columns: group names and rgb colors
         */

        $('body').append('<input id="loadGroups" type="file" />');

        /*
         * After selecting a file, this triggers loadGroups function
         */

        $('#loadGroups').on('change', function (e) {
            loadGroups(e);
        });

        /*
         * Clear the input field on each 'click', thus allowing to read the
         * same file after it is modified externally. Otherwise, the file
         * won't load a second time it is opened!
         */

        $('#loadGroups').on('click', function () {
            this.value = null;
        });

        /*
         * Use w2ui to build the group's grid
         */

        $().w2grid({
            name: 'groups', multiSelect: false, show: {
                header: false,
                toolbar: true,
                footer: true,
                lineNumbers: false,
                toolbarSearch: false,
                toolbarInput: false,
                toolbarReload: false,
                toolbarColumns: false,
                toolbarSave: false,
                toolbarAdd: false,
                toolbarDelete: false,
                toolbarEdit: false
            }, columns: [{
                field: 'recid',
                caption: 'Group',
                size: '45%',
                sortable: true,
                resizable: false,
                editable: {type: 'text'},
                render: function (r) {
                    return '<div style="font-weight: bold">' + r.recid + '</div>';
                }
            }, {
                field: 'color',
                caption: 'Color',
                size: '20%',
                sortable: false,
                resizable: false,
                editable: {type: 'color'},
                render: function (r) {
                    return '<div style="background-color: #' + r.color + '">&nbsp;</div>';
                }
            }, {
                field: 'pattern',
                caption: 'Pattern',
                size: '35%',
                sortable: false,
                resizable: false,
                editable: {type: 'combo', items: pattern_names, filter: false},
                render: function (r) {
                    return '<div>' + r.pattern + '</div>';
                }
            }], records: [{recid: 'Default', color: defaultGroupColor, pattern: 'none'}], toolbar: {
                items: [{type: 'button', id: 'add_group', caption: 'Add', icon: 'w2ui-icon-plus'}, {
                    type: 'button', id: 'del_group', caption: 'Delete', icon: 'w2ui-icon-cross'
                }, {type: 'button', id: 'load_group', caption: 'Load', icon: 'icon-folder-open'}, {
                    type: 'button', id: 'save_group', caption: 'Save', icon: 'icon-file-save'
                }], onClick: function (e) {
                    switch (e.target) {
                        case 'add_group':
                            e.preventDefault();

                            /*
                             * Check if a group with the default name ('New Group') exists! If so get out...
                             */

                            var v = w2ui.groups.find({recid: 'New Group'}, true);
                            if (v.length > 0) w2alert('A group named "New Group" already exists! <p> Change its name first...'); else {
                                w2ui.groups.add({recid: 'New Group', color: 'ffffff', pattern: 'none'});
                                this.refresh();
                            }
                            break;
                        case 'del_group':
                            e.force = true;
                            var sel = w2ui.groups.getSelection()[0];


                            /*
                             * Check if selected group is the default one [0]
                             */

                            if (sel === 0 || sel === 'Default') {
                                e.preventDefault();
                                w2alert('Cannot delete "default" group/color...');
                            } else {

                                /*
                                 * Check if 'haplotype' grid is already defined and that no
                                 * record of w2ui.haplotypes references this record from w2ui.groups
                                 */

                                if (w2ui.haplotypes) {
                                    var h = w2ui.haplotypes.records.filter(function (o) {
                                        return o.group === sel;
                                    });
                                    if (h.length > 0) {
                                        e.preventDefault();
                                        w2alert('This group is being referenced in haplotype list!<p>Change it there, and then delete it...');
                                    } else {
                                        w2ui.groups.delete(true);
                                    }
                                } else w2ui.groups.delete(true);
                            }
                            break;
                        case 'load_group':
                            if (nodeList.length === 0) {
                                w2alert('Please load graph data first via the "Load Data" button<br>before importing a group configuration file.', 'No graph data!');
                            } else {
                                $('#loadGroups').click();
                            }
                            break;
                        case 'save_group':
                            saveGroups();
                            break;
                    }

                    if (legend === 1) {
                        $('.legend').remove();
                        legend = 0;
                        insertLegend();
                    }
                }
            }, onChange: function (e) {
                var i;
                e.preventDefault();
                var groupName = w2ui.groups.records[e.index].recid;
                switch (e.column) {
                    case 0:  // Change a name

                        if (groupName === 'Default') {
                            w2alert('The Default group name is fixed; its color can be edited.');
                            break;
                        }

                        /*
                         * Check if a group with the same name already exists! If so get out...
                         */

                        var v = w2ui.groups.find({recid: e.value_new}, true);
                        if (v.length > 0) {
                            w2alert('A group named "' + e.value_new + '" already exists! <p> Change its name first...');
                        } else {
                            w2ui.groups.records[e.index].recid = e.value_new;

                            /*
                             * If this name is in haplotype list, change it as well
                             */

                            v = w2ui.haplotypes.find({group: e.value_original}, true);
                            if (typeof v !== 'undefined' && v.length > 0) {
                                for (i = 0; i < v.length; i++) {
                                    w2ui.haplotypes.records[v[i]].group = e.value_new;
                                    if (svg) classify(v[i], e.value_new, e.value_original);
                                }
                            }
                            if (hasMeta) syncMetaGroupName(
                                e.value_original, e.value_new);
                        }
                        break;
                    case 1: // Change a color

                        w2ui.groups.records[e.index].color = e.value_new;
                        if (groupName === 'Default') defaultGroupColor = e.value_new;

                        /*
                         * If there is a pattern, update it
                         */

                        if (w2ui.groups.records[e.index].pattern !== 'none') {
                            $("#" + e.value_original + w2ui.groups.records[e.index].pattern).remove();
                            createPattern(w2ui.groups.records[e.index].pattern, e.value_new);
                        }


                        /*
                         * If this name is in haplotype list, change its color as well
                         */

                        v = w2ui.haplotypes.find({group: groupName}, true);
                        if (typeof v !== 'undefined' && v.length > 0) {
                            for (i = 0; i < v.length; i++) {
                                w2ui.haplotypes.records[v[i]].color = e.value_new;
                                if (svg) classify(v[i], groupName, groupName);
                            }
                        }
                        if (hasMeta) syncMetaGroupColor(groupName, e.value_new);
                        break;

                    case 2: // Change a pattern

                        if (groupName === 'Default') {
                            w2alert('The Default group pattern is fixed; its color can be edited.');
                            break;
                        }

                        w2ui.groups.records[e.index].pattern = e.value_new;

                        /*
                         * Update the SVG
                         */

                        if (svg) {
                            var c = w2ui.groups.records[e.index].color;
                            if (e.value_original !== 'none') $("#" + c + e.value_original).remove();
                            if (e.value_new !== 'none') createPattern(e.value_new, c);

                            /*
                             * Reclassify any haloptypes that belong to this group
                             */

                            v = w2ui.haplotypes.find({group: groupName}, true);
                            if (typeof v !== 'undefined' && v.length > 0) {
                                for (i = 0; i < v.length; i++) {
                                    classify(v[i], groupName, groupName);
                                }
                            }
                        }
                        break;
                }

                // Rebuild the graph after a Groups edit.  This is required for
                // NetST metadata rings as well as the classic group pie.
                if (svg) updateSVG();
                if (w2ui.haplotypes) w2ui.haplotypes.refresh();
                if (hasMeta) refreshMetaLegend();

                /*
                 * If legend is present, delete it and redraw it
                 */

                if (legend === 1) {
                    $('.legend').remove();
                    legend = 0;
                    insertLegend();
                }

                this.refresh();
            }
        });
        if (w2ui.groups) return w2ui.groups; else return null;
    }

    /*
     * The haplotypes grid.
     * Builds the w2ui grid that lists all haplotypes with their group assignment,
     * sequence-to-haplotype mapping, and highlight/label status.
     */
    function getHaplotypesGrid() {

        /*
         * Append a hidden <input> element at the end of the body. This will serve as an anchor
         * used by button 'loadHaplotypes' to browse files for reading a haplotype's CSV file
         * (semicolon-delimited text with columns: haplotype name, group, seq2hap).
         */

        $('body').append('<input id="loadHaplotypes" type="file" />');

        /*
         * After selecting a file, this triggers loadHaplotypes function
         */

        $('#loadHaplotypes').on('change', function (e) {
            loadHaplotypes(e);
        });

        $().w2grid({
            name: 'haplotypes', multiSelect: true, show: {
                header: false,
                toolbar: true,
                footer: true,
                lineNumbers: false,
                toolbarSearch: false,
                toolbarInput: false,
                toolbarReload: false,
                toolbarColumns: false,
                toolbarAdd: false,
                toolbarDelete: false,
                toolbarEdit: false
            }, columns: [{
                field: 'recid', caption: 'Id', // size: '40%',
                sortable: true, resizable: true
            }, {field: 'haplogroup', hidden: true}, {field: 'color', hidden: true}, {
                field: 'group',
                caption: 'Group', // size: '24%',
                sortable: true,
                resizable: true,
                editable: {type: 'combo', items: ['Default'], filter: false},
                render: function (r) {
                    var color = parseInt(r.color, 16);
                    var textcolor;
                    if (color > 8388607) textcolor = '#000000'; else textcolor = '#ffffff';
                    return '<div style="background-color: #' + r.color + '; color: ' + textcolor + '">' + r.group + '</div>';
                }
            }, {
                field: 'seq2hap', caption: 'SeqHap', sortable: true, resizable: true
            }], toolbar: {
                items: [{
                    type: 'button', id: 'load_haplotypes', text: 'Load', icon: 'icon-folder-open'
                }, {type: 'button', id: 'save_haplotypes', text: 'Save', icon: 'icon-file-save'}
                ], onClick: function (e) {
                    switch (e.target) {
                        case 'load_haplotypes':
                            if (w2ui.haplotypes.records.length === 0) {
                                w2alert('Please load graph data first via the "Load Data" button<br>before importing a haplotype configuration file.', 'No graph data!');
                            } else if (w2ui.groups.records.length <= 1) {
                                w2alert('Please load a group configuration file first<br>before importing a haplotype configuration file.', 'No group data!');
                            } else {
                                $('#loadHaplotypes').click();
                            }
                            break;
                        case 'save_haplotypes':
                            saveHaplotypes();
                            break;
                    }
                }
            }, onChange: function (e) {
                e.preventDefault();

                /*
                 * get the new group index of this particular haplotype
                 */

                var r = w2ui.groups.find({recid: e.value_new}, true)[0];

                /*
                 * if groups' name exist just change the name and color in haplotypes.
                 * Otherwise use defaults
                 */

                if (typeof r !== 'undefined') {
                    w2ui.haplotypes.records[e.index].group = w2ui.groups.records[r].recid;
                    w2ui.haplotypes.records[e.index].color = w2ui.groups.records[r].color;
                } else {
                    w2ui.haplotypes.records[e.index].group = 'Default';
                    w2ui.haplotypes.records[e.index].color = defaultGroupColor;
                }

                classify(e.index, e.value_new, e.value_original);
                if (hasMeta) {
                    syncMetaHaplotypeGroup(
                        w2ui.haplotypes.records[e.index].recid,
                        w2ui.haplotypes.records[e.index].group);
                }
            }, onEditField: function () {
                var items = [];
                var grplist = w2ui.groups.records;
                for (var i = 0; i < grplist.length; i++) {
                    items.push(grplist[i].recid);
                }
                this.columns[3].editable.items = items;
            }
        });
        if (w2ui.haplotypes) return w2ui.haplotypes; else return null;
    }

    function formatMetaLegendNumber(value) {
        var number = Number(value);
        if (!isFinite(number)) return '';
        return String(parseFloat(number.toPrecision(6)));
    }

    function legendTransform(state) {
        return 'translate(' + state.x + ',' + state.y + ') scale(' + state.scale + ')';
    }

    /*
     * Keep legend resizing independent from the network zoom. Hover a legend
     * and use the mouse wheel to resize it around the pointer; double-clicking
     * restores its original size. Stopping the wheel event here prevents the
     * main SVG zoom handler from scaling the network at the same time.
     */
    function enableLegendScaling(legendSelection) {
        legendSelection
            .on('wheel.legend-scale', function (state) {
                var event = d3.event;
                if (!state || !event) return;

                if (event.preventDefault) event.preventDefault();
                if (event.stopPropagation) event.stopPropagation();

                var delta = 0;
                if (typeof event.deltaY === 'number') delta = -event.deltaY;
                else if (typeof event.wheelDelta === 'number') delta = event.wheelDelta;
                else if (typeof event.detail === 'number') delta = -event.detail;
                if (delta === 0) return;

                var oldScale = state.scale || 1;
                var factor = delta > 0 ? 1.1 : (1 / 1.1);
                var newScale = Math.max(
                    legendMinScale,
                    Math.min(legendMaxScale, oldScale * factor)
                );
                if (newScale === oldScale) return;

                var root = document.getElementById('SVG');
                if (root) {
                    var pointer = d3.mouse(root);
                    state.x = pointer[0] - (pointer[0] - state.x) * newScale / oldScale;
                    state.y = pointer[1] - (pointer[1] - state.y) * newScale / oldScale;
                }
                state.scale = newScale;
                d3.select(this).attr('transform', legendTransform(state));
            })
            .on('dblclick.legend-scale', function (state) {
                var event = d3.event;
                if (!state || !event) return;
                if (event.preventDefault) event.preventDefault();
                if (event.stopPropagation) event.stopPropagation();
                state.scale = 1;
                d3.select(this).attr('transform', legendTransform(state));
            });

        legendSelection.append('title')
            .text('Drag to move. Scroll to resize. Double-click to reset size.');
    }

    /*
     * Draw one draggable legend containing every visible metadata ring in the
     * same inner-to-outer order as the nodes. Discrete traits get categorical
     * swatches; continuous traits get their own low-to-high gradient and
     * numeric range.
     */
    function insertMetaLegend(svgEl) {
        var traits = (metaConfig && metaConfig.traits) || [];
        if (traits.length === 0) return;

        var coords = {x: 50, y: 100, scale: 1};
        var legendG = svgEl.append('g')
            .datum(coords)
            .attr('transform', legendTransform(coords))
            .attr('class', 'legend legend-meta')
            // Qt 6.11.0/6.11.1 on macOS renders CSS "move" as a pixmap
            // cursor and can crash in QImage::toCGImage (QTBUG-147602).
            // "grab" uses the native OpenHandCursor and keeps drag behaviour.
            .style('cursor', 'grab');
        enableLegendScaling(legendG);
        var background = legendG.append('rect')
            .attr('class', 'meta-legend-background')
            .attr('fill', 'white')
            .attr('stroke', '#555')
            .attr('stroke-width', 0.7)
            .attr('rx', 3);
        var content = legendG.append('g')
            .attr('class', 'meta-legend-content')
            .attr('transform', 'translate(10,10)');
        var cursorY = 0;

        for (var t = 0; t < traits.length; t++) {
            var trait = traits[t] || {};
            var title = 'Ring ' + (t + 1) + ' \u00b7 ' + (trait.name || 'Trait');

            content.append('text')
                .attr('x', 0).attr('y', cursorY + 12)
                .style('font-size', '12px')
                .style('font-weight', 'bold')
                .text(title);
            cursorY += 22;

            if (trait.kind === 'continuous') {
                var gradient = trait.gradient || ['#BDBDBD', '#000000'];
                var gradientId = 'metaLegendGradient' + t;
                var defs = svgEl.select('defs');
                if (defs.empty()) defs = svgEl.append('defs');
                var linear = defs.append('linearGradient')
                    .attr('id', gradientId)
                    .attr('class', 'meta-legend-gradient')
                    .attr('x1', '0%').attr('y1', '0%')
                    .attr('x2', '100%').attr('y2', '0%');
                linear.append('stop')
                    .attr('offset', '0%')
                    .attr('stop-color', gradient[0] || '#BDBDBD');
                linear.append('stop')
                    .attr('offset', '100%')
                    .attr('stop-color', gradient[1] || '#000000');

                content.append('rect')
                    .attr('x', 0).attr('y', cursorY)
                    .attr('width', 170).attr('height', 16)
                    .attr('fill', 'url(#' + gradientId + ')')
                    .attr('stroke', '#777').attr('stroke-width', 0.5);
                content.append('text')
                    .attr('x', 0).attr('y', cursorY + 30)
                    .style('font-size', '10px')
                    .text(formatMetaLegendNumber(trait.vmin));
                content.append('text')
                    .attr('x', 170).attr('y', cursorY + 30)
                    .attr('text-anchor', 'end')
                    .style('font-size', '10px')
                    .text(formatMetaLegendNumber(trait.vmax));
                cursorY += 40;
            } else {
                var categories = (trait.categories || []).slice();
                if (trait.has_missing) {
                    categories.push({label: '(missing)', color: '#DDDDDD'});
                }
                if (categories.length === 0) {
                    categories.push({label: '(unassigned)', color: '#DDDDDD'});
                }
                var columnCount = categories.length > 10 ? 2 : 1;
                var rowCount = Math.ceil(categories.length / columnCount);
                var columnWidth = 155;
                for (var c = 0; c < categories.length; c++) {
                    var column = Math.floor(c / rowCount);
                    var row = c % rowCount;
                    var x = column * columnWidth;
                    var y = cursorY + row * 18;
                    content.append('rect')
                        .attr('x', x).attr('y', y)
                        .attr('width', 13).attr('height', 13)
                        .attr('fill', categories[c].color || '#DDDDDD')
                        .attr('stroke', '#777').attr('stroke-width', 0.5);
                    content.append('text')
                        .attr('x', x + 19).attr('y', y + 11)
                        .style('font-size', '10px')
                        .text(categories[c].label || '(missing)');
                }
                cursorY += rowCount * 18 + 4;
            }

            if (t < traits.length - 1) {
                content.append('line')
                    .attr('x1', 0).attr('x2', 170)
                    .attr('y1', cursorY + 2).attr('y2', cursorY + 2)
                    .attr('stroke', '#DDDDDD').attr('stroke-width', 0.7);
                cursorY += 10;
            }
        }

        var box = content.node().getBBox();
        background
            .attr('x', 0).attr('y', 0)
            .attr('width', Math.max(205, box.width + 20))
            .attr('height', Math.max(35, box.height + 20));

        var dragLegend = d3.behavior.drag()
            .on('drag', function (d) {
                d.x += d3.event.dx;
                d.y += d3.event.dy;
                d3.select(this)
                    .attr('transform', legendTransform(d));
            })
            .on('dragstart', function () {
                d3.event.sourceEvent.stopPropagation();
            });
        legendG.call(dragLegend);
    }

    function insertLegend() {
        if (legend === 0) {
            legend = 1;
            var svgEl = d3.select('svg');

            if (hasMeta && metaConfig) {
                insertMetaLegend(svgEl);
                return;
            }

            // styleid 0 (Dual-Trait) or 1 (Category): show group legend
            if (styleid === 0 || styleid === 1) {
                var grouplist = [];
                var colorlist = [];
                var g = w2ui.groups.records;
                for (var i = 1; i < g.length; i++) {
                    grouplist.push(g[i].recid);
                    if (g[i].pattern !== 'none') colorlist.push("url(#" + g[i].color + g[i].pattern + ")"); else colorlist.push('#' + g[i].color);
                }
                var lg = d3.scale.ordinal();
                lg.domain(grouplist);
                lg.range(colorlist);
                var verticalLegend = d3.svg.legend().labelFormat('none').cellPadding(5).orientation('vertical').units('Groups').cellWidth(25).cellHeight(18).inputScale(lg).cellStepping(10);
                var groupLegendState = {x: 50, y: 140, scale: 1};
                var groupLegend = svgEl.append('g')
                    .datum(groupLegendState)
                    .attr('transform', legendTransform(groupLegendState))
                    .attr('class', 'legend')
                    .call(verticalLegend);
                enableLegendScaling(groupLegend);
            }

            // styleid 0 (Dual-Trait) or 2 (Continuous): show trait gradient bar
            if ((styleid === 0 || styleid === 2) && typeid !== 4 && hasTrait) {
                var minColor = tcGradient('08', typeid);
                var maxColor = tcGradient('f7', typeid);

                var gradBarW = 20, gradBarH = 120;
                var gradX = 50;
                var gradY = 140;
                if (styleid === 0) {
                    var groupCount = Math.max(0, w2ui.groups.records.length - 1);
                    gradY = 140 + 35 + groupCount * 28 + 15;
                }

                // Add linearGradient def (top = max color, bottom = min color — reversed so min label at top reads correctly)
                var defs = svgEl.select('defs');
                if (defs.empty()) defs = svgEl.append('defs');
                var grad = defs.append('linearGradient')
                    .attr('id', 'legendGradient')
                    .attr('x1', '0%').attr('y1', '0%')
                    .attr('x2', '0%').attr('y2', '100%');
                grad.append('stop').attr('offset', '0%').attr('stop-color', maxColor);
                grad.append('stop').attr('offset', '100%').attr('stop-color', minColor);

                var traitCoords = {x: gradX, y: gradY, scale: 1};
                var legendG = svgEl.append('g')
                    .data([traitCoords])
                    .attr('transform', legendTransform(traitCoords))
                    .attr('class', 'legend legend-trait')
                    // Avoid Qt's crashing macOS pixmap cursor path; D3 owns
                    // the actual drag behaviour, so only the hint changes.
                    .style('cursor', 'grab');
                enableLegendScaling(legendG);

                // Drag — same pattern as group legend
                var drag = d3.behavior.drag()
                    .on('drag', function (d) {
                        d.x += d3.event.dx;
                        d.y += d3.event.dy;
                        d3.select(this).attr('transform', legendTransform(d));
                    })
                    .on('dragstart', function () {
                        d3.event.sourceEvent.stopPropagation();
                    });
                legendG.call(drag);

                // Background
                legendG.append('rect')
                    .attr('x', -5).attr('y', -5)
                    .attr('width', gradBarW + 70).attr('height', gradBarH + 45)
                    .attr('fill', 'white').attr('stroke', 'black').attr('stroke-width', 0.5).attr('rx', 2);

                // Title
                legendG.append('text')
                    .attr('x', 0).attr('y', 10)
                    .style('font-size', '12px').style('font-weight', 'bold')
                    .text('Trait');

                // Min label (top)
                legendG.append('text')
                    .attr('x', gradBarW + 5).attr('y', 30)
                    .style('font-size', '10px')
                    .text(minTime);

                // Gradient color bar
                legendG.append('rect')
                    .attr('x', 0).attr('y', 20)
                    .attr('width', gradBarW).attr('height', gradBarH)
                    .attr('fill', 'url(#legendGradient)');

                // Gradient bar border
                legendG.append('rect')
                    .attr('x', 0).attr('y', 20)
                    .attr('width', gradBarW).attr('height', gradBarH)
                    .attr('fill', 'none').attr('stroke', '#888').attr('stroke-width', 0.5);

                // Max label (bottom)
                legendG.append('text')
                    .attr('x', gradBarW + 5).attr('y', 20 + gradBarH)
                    .style('font-size', '10px')
                    .text(maxTime);
            }
        } else {
            legend = 0;
            $('.legend').remove();
            d3.select('#legendGradient').remove();
            d3.selectAll('.meta-legend-gradient').remove();
        }
    }

    /*
     * Construct the layout
     */

    function getLayout(style, groups, haplotypes) {
        $('#layout').w2layout({
            name: 'Layout', padding: 0, panels: [
                {type: 'top', size: 40, resizable: false, style: style},
                {
                    type: 'left', size: 350, resizable: true, title: 'Data', style: style, tabs: {
                        name: 'tabs',
                        active: 'tab1',
                        // Trait visualization is configured in NetST's
                        // Metadata tab; this panel keeps only editable group
                        // and haplotype assignments.
                        tabs: [
                            {id: 'tab2', text: 'Groups'},
                            {id: 'tab1', text: 'Haplotypes'}
                        ],
                        onClick: function (id) {
                            switch (id.target) {
                                case 'tab1':
                                    w2ui.Layout.content('left', haplotypes);
                                    break;
                                case 'tab2':
                                    w2ui.Layout.content('left', groups);
                                    break;
                            }
                        }

                    }
                }, {type: 'right', size: 280, resizable: true, title: 'Haplotype Network Info', style: style}, {
                    type: 'main', size: '100%', overflow: 'hidden', style: style, toolbar: {
                        items: [{
                            id: 'btn-saveimage', type: 'menu', text: 'Save Image', icon: 'icon-file-svg',
                            disabled: true, items: [
                                {id: 'svg', text: 'SVG (vector)'},
                                {id: 'png', text: 'PNG'},
                                {id: 'jpg', text: 'JPG'},
                                {id: 'pdf', text: 'PDF'}
                            ]
                        },
                            {type: 'break'}, {
                                id: 'btn-zoomin',
                                class: 'zoom-btn',
                                type: 'button',
                                text: 'Zoom In',
                                icon: 'icon-zoom-in',
                                disabled: true
                            }, {
                                id: 'btn-zoomout',
                                class: 'zoom-btn',
                                type: 'button',
                                text: 'Zoom Out',
                                icon: 'icon-zoom-out',
                                disabled: true
                            }, {type: 'break'}, {
                                id: 'btn-delnode',
                                type: 'check',
                                text: 'Delete Node',
                                icon: 'icon-delete-node',
                                disabled: true,
                                checked: false
                            }, {
                                id: 'btn-dellink',
                                type: 'check',
                                text: 'Delete Link',
                                icon: 'icon-delete-link',
                                disabled: true,
                                checked: false
                            }, {type: 'break'}, {
                                id: 'btn-legend',
                                type: 'check',
                                text: 'Legend',
                                icon: 'icon-legend',
                                disabled: true,
                                checked: false
                            },
                            // Buttons for toggling haplotype labels and link-distance annotations.
                            {
                                id: 'btn-haplotype',
                                type: 'check',
                                text: 'Haplotype',
                                icon: 'icon-label',
                                disabled: true,
                                checked: false
                            }, {
                                id: 'btn-name-id',
                                type: 'check',
                                text: 'Name/ID',
                                icon: 'icon-label',
                                disabled: true,
                                checked: false
                            }, {
                                id: 'btn-distance',
                                type: 'check',
                                text: 'Distance',
                                icon: 'icon-label',
                                disabled: true,
                                checked: false
                            }, {
                                id: 'btn-edgeweight',
                                type: 'check',
                                text: 'Edge Weight',
                                icon: 'icon-line-width',
                                disabled: true,
                                checked: false
                            }, {type: 'break'}, {
                                id: 'btn-undo',
                                type: 'button',
                                text: 'Undo',
                                icon: 'icon-label',
                                disabled: true
                            }, {type: 'break'}, {
                                id: 'btn-advanced',
                                type: 'button',
                                text: 'Advanced',
                                icon: 'icon-advanced',
                                disabled: true
                            },], onClick: function (e) {
                            var target = e.target;
                            switch (target) {
                                case 'btn-dellink':
                                    deletelink = !e.item.checked;
                                    break;
                                case 'btn-delnode':
                                    deletenode = !e.item.checked;
                                    break;
                                case 'btn-zoomin':
                                    zoomByFactor(1.2);
                                    break;
                                case 'btn-zoomout':
                                    zoomByFactor(0.8);
                                    break;
                                case 'btn-legend':
                                    insertLegend();
                                    break;
                                case 'btn-haplotype':
                                    insertHaplotype();
                                    break;
                                case 'btn-name-id':
                                    insertNameId();
                                    break;
                                case 'btn-distance':
                                    insertDistance();
                                    break;
                                case 'btn-edgeweight':
                                    toggleEdgeWeight();
                                    break;
                                case 'btn-undo':
                                    undoDelete();
                                    break;
                                case 'btn-advanced':
                                    openAdvancedSettings();
                                    break;
                            }
                            if (target.indexOf('btn-saveimage:') === 0) {
                                saveImage(target.split(':')[1]);
                            } else if (target === 'btn-saveimage' && e.subItem) {
                                saveImage(e.subItem.id);
                            }
                        },
                    },
                }
                //{ type: 'bottom', size: 30, resizable: false, style: style, content: 'Start'}
            ],
        });
        if (w2ui.Layout) return w2ui.Layout; else return null;
    }

    /*
     *
     * legend.js was modified from https://github.com/emeeks/d3-svg-legend/blob/master/legend.js
     * authored by Michael P Schroeder (mpschr)
     *
     * It is used under the following licence (https://github.com/emeeks/d3-svg-legend/blob/master/LICENSE)
     *
     * This is free and unencumbered software released into the public domain.
     *
     * Anyone is free to copy, modify, publish, use, compile, sell, or
     * distribute this software, either in source code form or as a compiled
     * binary, for any purpose, commercial or non-commercial, and by any
     * means.
     *
     * In jurisdictions that recognize copyright laws, the author or authors
     * of this software dedicate any and all copyright interest in the
     * software to the public domain. We make this dedication for the benefit
     * of the public at large and to the detriment of our heirs and
     * successors. We intend this dedication to be an overt act of
     * relinquishment in perpetuity of all present and future rights to this
     * software under copyright law.
     *
     * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
     * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
     * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
     * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
     * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
     * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
     * OTHER DEALINGS IN THE SOFTWARE.
     *
     * For more information, please refer to <http://unlicense.org>
     */


    d3.svg.legend = function () {

        var legendValues = [];
        var cellWidth = 80;
        var cellHeight = 30;
        var labelFormat = d3.format(".01f");
        var coordinates = {x: 0, y: 0};
        var labelUnits = "units";
        var changeValue = 1;
        var orientation = "horizontal";
        var cellPadding = 0;


        function legend(svg) {

            var updateBGSize = function (legend) {

                var margin = 10;
                var dim = legend.target.node().getBBox();
                dim.height += margin * 2;
                dim.width += margin * 2;
                dim.y -= margin;
                dim.x -= margin;

                legend.parentGroup.select(".mutLegendBG").attr(dim);
            };

            var drag = d3.behavior.drag()
                .on("drag", function (d) {
                    d.x += d3.event.dx;
                    d.y += d3.event.dy;
                    d3.select(this).attr("transform", function (d) {
                        return "translate(" + [d.x, d.y] + ")";
                    });
                })
                .on("dragstart", function () {
                    d3.event.sourceEvent.stopPropagation(); // silence other listeners
                });

            function init() {
                var mutLegendGroup = svg.append("g")
                    .attr("class", "mutLegendGroup")
                    .data([coordinates])
                    .attr("transform", "translate(" + coordinates.x + "," + coordinates.y + ")");
                var target = mutLegendGroup
                    .insert("g")
                    .attr("class", "mutLegendGroupText");


                // set legend background
                var mutLegendBG = mutLegendGroup
                    .insert("rect", ":first-child")
                    .attr("class", "mutLegendBG")
                    .attr("fill", "white")
                    .attr("stroke", "black")
                    .attr("stroke-width", "1px");


                return {
                    parentGroup: mutLegendGroup, target: target
                };
            }


            function cellRange(valuePosition, changeVal) {
                legendValues[valuePosition].stop[0] += changeVal;
                legendValues[valuePosition - 1].stop[1] += changeVal;
                redraw();
            }

            function redraw() {
                legend.target.selectAll("g.legendCells").data(legendValues).exit().remove();
                legend.target.selectAll("g.legendCells").select("rect")
                    .style("fill", function (d) {
                        return d.color;
                    });
                if (orientation === "vertical") {
                    legend.target.selectAll("g.legendCells").select("text.breakLabels").style("display", "block").style("text-anchor", "start").attr("x", cellWidth + cellPadding).attr("y", 5 + (cellHeight / 2)).text(function (d) {
                        return labelFormat(d.stop[0]) + (d.stop[1].length > 0 ? " - " + labelFormat(d.stop[1]) : "");
                    });
                    legend.target.selectAll("g.legendCells").attr("transform", function (d, i) {
                        return "translate(0," + (i * (cellHeight + cellPadding)) + ")";
                    });
                } else {
                    legend.target.selectAll("g.legendCells").attr("transform", function (d, i) {
                        return "translate(" + (i * cellWidth) + ",0)";
                    });
                    legend.target.selectAll("text.breakLabels").style("text-anchor", "middle").attr("x", 0).attr("y", -7).style("display", function (d, i) {
                        return i === 0 ? "none" : "block";
                    }).text(function (d) {
                        return labelFormat(d.stop[0]);
                    });
                }
            }

            // init
            if (!legend.initDone) {
                var initObj = init();
                legend.target = initObj.target;
                legend.parentGroup = initObj.parentGroup;
                legend.parentGroup.call(drag);
                legend.initDone = true;
            }


            // remove previously painted rect and text
            legend.target.selectAll("g.legendCells").select("text.breakLabels").remove();
            legend.target.selectAll("g.legendCells").select("rect").remove();
            legend.target.selectAll(".legendTitle").remove();


            legend.target.selectAll("g.legendCells")
                .data(legendValues)
                .enter()
                .append("g")
                .attr("class", "legendCells")
                .attr("transform", function (d, i) {
                    return "translate(" + (i * (cellWidth + cellPadding)) + ",0)";
                });

            legend.target.selectAll("g.legendCells")
                .append("rect")
                .attr("class", "breakRect")
                .attr("height", cellHeight)
                .attr("width", cellWidth)
                .style("fill", function (d) {
                    return d.color;
                })
                .style("stroke", function () {
                    return "#000000"; /*d3.rgb(d.color).darker(); */
                });

            legend.target.selectAll("g.legendCells")
                .append("text")
                .attr("class", "breakLabels")
                .style("pointer-events", "none");

            legend.target.append("text")
                .text(labelUnits)
                .attr("y", -7)
                .attr("class", "legendTitle");

            redraw();
            updateBGSize(legend);
        }

        legend.initDone = false;
        legend.target = null; // will be set during init()

        legend.inputScale = function (newScale) {
            let scale;
            if (!arguments.length) return scale;
            scale = newScale;
            legendValues = [];
            if (scale.invertExtent) {
                //Is a quantile scale
                scale.range().forEach(function (el) {
                    var cellObject = {color: el, stop: scale.invertExtent(el)};
                    legendValues.push(cellObject);
                });
            } else {
                scale.domain().forEach(function (el) {
                    var cellObject = {color: scale(el), stop: [el, ""]};
                    legendValues.push(cellObject);
                });
            }
            return this;
        };

        legend.scale = function (testValue) {
            var foundColor = legendValues[legendValues.length - 1].color;
            for (var el in legendValues) {
                if (testValue < legendValues[el].stop[1]) {
                    foundColor = legendValues[el].color;
                    break;
                }
            }
            return foundColor;
        };

        legend.cellWidth = function (newCellSize) {
            if (!arguments.length) return cellWidth;
            cellWidth = newCellSize;
            return this;
        };

        legend.cellHeight = function (newCellSize) {
            if (!arguments.length) return cellHeight;
            cellHeight = newCellSize;
            return this;
        };

        legend.cellPadding = function (newCellPadding) {
            if (!arguments.length) return cellPadding;
            cellPadding = newCellPadding;
            return this;
        };

        legend.cellExtent = function (incColor, newExtent) {
            var selectedStop = legendValues.filter(function (el) {
                return el.color === incColor;
            })[0].stop;
            if (arguments.length === 1) return selectedStop;
            legendValues.filter(function (el) {
                return el.color === incColor;
            })[0].stop = newExtent;
            return this;
        };

        legend.cellStepping = function (incStep) {
            if (!arguments.length) return changeValue;
            changeValue = incStep;
            return this;
        };

        legend.units = function (incUnits) {
            if (!arguments.length) return labelUnits;
            labelUnits = incUnits;
            return this;
        };

        legend.orientation = function (incOrient) {
            if (!arguments.length) return orientation;
            orientation = incOrient;
            return this;
        };

        legend.labelFormat = function (incFormat) {
            if (!arguments.length) return labelFormat;
            labelFormat = incFormat;
            if (incFormat === "none") {
                labelFormat = function (inc) {
                    return inc;
                };
            }
            return this;
        };

        legend.place = function (incCoordinates) {
            if (!arguments.length) return incCoordinates;
            coordinates = incCoordinates;
            return this;
        };

        return legend;

    };

    /*
    * Reads GML file (output of TCS) from localhost. Should be a .graph file
    * outputed from TCS (format is: Graphic Modelling Language - GML)
    */

    function loadGraph(e) {
        var haplos = [];
        var input = e.target;

        var fileInput = document.getElementById('loadGraph');

        /*
         * Read only one file, no more, no less
         */

        if (input.files.length !== 1) return;

        var reader = new FileReader();


        /*
         * clear nodes and edges lists
         */

        nodeList = [];
        edgeList = [];
        linkList = [];
        highlightLink = [];
        labelLink = {};
        highlightNode = [];
        labelNode = {};
        nameIdNode = {};
        nodeNameId = {};
        nodeTextLayout = {};
        activeInfoNode = null;
        refreshActiveNodeInfo = null;

        reader.onload = function () {
            var text = reader.result;
            var lines = text.split('\n');
            var newnode = false;
            var newedge = false;
            var multilabels = false;
            var frequency, radius, haplogroup, label, nodestyle, changes, source, target;
            var labels = [];
            for (var i = 0; i < lines.length; i++) {
                if (lines[i].indexOf('node [') === 3) {
                    newnode = true;
                    // GML labels do not determine whether a node is inferred.
                    // That state is evaluated dynamically from Name/ID + group.
                    nodestyle = 1;
                }
                if (lines[i].indexOf('edge [') === 3) newedge = true;
                if (lines[i].indexOf(']') === 3) {
                    if (newnode) {
                        newnode = false;
                        if (labels.length > 0) {
                            radius = standardRadius;
                            if (nodestyle === 1) {

                                /* This is a true haplotype (not a transition node). Add it
                                 * to the haplotypes' list that will be presented in the grid
                                 * 'haplotypes'. Make sure labels start with a character (not
                                 * a digit) and have only [a-zA-Z0-9_-] characters. Replace all
                                 * other characters by '_'. The reason for this is that although
                                 * JQuery can handle most of these and other characters as
                                 * element's ids, d3.js is much more restrictive...
                                 */
                                for (var j = 0; j < labels.length; j++) {
                                    labels[j] = labels[j].replace(/[\W]/g, "_");


                                    /*
                                     * Test if the first characters is a digit. If so, prepend
                                     * the label with 'L'.
                                     */
                                    if (/^\d+$/.test(labels[j][0])) labels[j] = 'L' + labels[j];

                                    haplos.push({
                                        recid: labels[j],
                                        haplogroup: haplogroup,
                                        group: 'Default',
                                        color: defaultGroupColor,
                                        nodestyle: nodestyle,
                                        count: 1,
                                    });
                                }

                                /* Set the SVG radius of the haplogroup to a standard size, based
                                 * on the number of haplotypes in the haplogroup ('frequency')
                                 * times 'standardRadius'. standardRadius is defined as a global variable.
                                 * For transition nodes use a radius = frequency*standardRadius;
                                 */

                                // radius = Math.sqrt(frequency * area / Math.PI);
                                radius = Math.pow(frequency, 1 / 3) * standardRadius;
                            }
                            var labelname = labels.join("\n");
                            /*
                             * Push the nodes (haplogroups) into a nodeList, naming them by
                             * the first label if they include more than one
                             */

                            if (nodestyle === 0) radius = ancestorRadius;
                            nodeList.push({
                                name: labelname, radius: radius, nodestyle: nodestyle, proportions: [{
                                    group: 'Default',
                                    value: frequency,
                                    radius: radius,
                                    color: '#' + defaultGroupColor,
                                    pattern: 'none',
                                }], timeProportions: []
                                , id: haplogroup, //  label holds the info which should be shown
                                hap: null,
                            });

                            /*
                             * clear the labels list for next haplogroup
                             */

                            labels = [];
                        }
                    } else {
                        if (newedge) {
                            newedge = false;
                            edgeList.push({source: source, target: target, id: labels[0], changes: changes});
                        } else {
                            console.log('Serious Error!');
                        }
                    }
                }
                if (newnode) {
                    if ((lines[i][0] === '"') && (multilabels)) multilabels = false;
                    if (multilabels) labels.push(lines[i].trim());
                    if (lines[i].indexOf('id') === 6) haplogroup = Number(lines[i].substr(9, 10).trim());
                    if (lines[i].indexOf('Frequency') === 9) {
                        frequency = Number(lines[i].substr(30, 10).trim());
                        if (frequency > 0) multilabels = true;
                    }
                    if (lines[i].indexOf('label') === 6) label = lines[i].substr(12, 100).replace(/"/g, ' ').trim();
                    //if(lines[i].indexOf('x') == 12) x = Number(lines[i].substr(14, 100).trim());
                    //if(lines[i].indexOf('y') == 12) y = Number(lines[i].substr(14, 100).trim());
                    //if(lines[i].indexOf('group') == 9) group = Number(lines[i].substr(15, 100).trim());
                }
                if (newedge) {
                    if (lines[i].indexOf('label') === 6) label = lines[i].substr(12, 100).replace(/"/g, '').trim();
                    if (lines[i].indexOf('Changes') === 9) changes = lines[i].substr(17, 100).replace(/"/g, '').replace(/\t/g, ' ').trim();
                    if (lines[i].indexOf('source') === 6) source = Number(lines[i].substr(13, 100).trim());
                    if (lines[i].indexOf('target') === 6) target = Number(lines[i].substr(13, 100).trim());
                }
            }
            /*
             * Reset trait state: inner ring is hidden until loadTraits is called.
             */
            hasTrait = false;
            minTime = Number.POSITIVE_INFINITY;
            maxTime = Number.NEGATIVE_INFINITY;

            /*
             * Reset hapconf state.
             */
            hapconfLoaded = false;
            hapconfColumns = 0;
            seqHapFlag = false;
            nameIdFlag = false;
            if (w2ui.Layout_main_toolbar) {
                w2ui.Layout_main_toolbar.uncheck('btn-haplotype', 'btn-name-id');
            }
            styleid = 1;
            // Clear any metadata rings from a previous graph; a pending config
            // (set after this load was queued) is preserved and applied below.
            hasMeta = false;
            metaConfig = null;

            /*
             * Clear any haplotypes present in the haplotypes' grid
             */

            if (w2ui.haplotypes.records.length > 0) w2ui.haplotypes.clear();

            /*
             * Clear any groups defined except Default
             */

            if (w2ui.groups.records.length > 1) {
                w2ui.groups.clear();
                w2ui.groups.add({recid: 'Default', color: defaultGroupColor, pattern: 'none'});
            }

            /*
             * Remove any previous svg elements
             */

            if (svg) {
                d3.select("#gview").selectAll("*").remove();
                svg = null;
                force = null;
            }


            /*
             * Add the new haplotypes to the grid
             */

            w2ui.haplotypes.add(haplos);

            /*
             * Disable start button
             */

            $('#start').prop('disabled', true);

            /*
             * clear input field so that file can be reopened!
             */

            fileInput.value = "";

            /*
             * start the d3 force layout
             */

            svgStart();

            // Apply a NetST metadata ring config that arrived before the graph
            // finished parsing (loadMetaConfig is synchronous; this onload is not).
            if (pendingMetaConfig) applyMetaConfig();

        };
        reader.readAsText(input.files[0]);
    }

    /*
     * Reads a CSV file with group names and colors
     */

    function loadGroups(event) {

        var input = event.target;
        // Read only one file, no more, no less

        if (input.files.length !== 1) return;

        var fileInput = document.getElementById('loadGroups');

        var reader = new FileReader();

        reader.onload = function () {
            var i, j, k, p;
            var text = reader.result;
            var lines = text.split('\n');
            var line, l, name, color, pattern;
            var names = ['Default'];
            var loadedGroups = 0;
            var g = [{recid: 'Default', color: defaultGroupColor, pattern: 'none'}];
            for (i = 0; i < lines.length; i++) {
                line = lines[i].trim();
                if (line !== '') {
                    l = line.split(";");
                    if (l.length === 2 || l.length === 3) {   // Accept only lines with two or three fields
                        name = l[0].trim();
                        if (name !== '') {                       // There is at least a label or name or something as a first field...
                            k = names.indexOf(name);                // Check if this name is already in list
                            if (k === -1 || name === 'Default') {
                                if (k === -1) names.push(name);       // Add name to the names' list
                                color = l[1].trim();                  // read the color
                                if (/^#[0-9a-f]{3,6}$/i.test(color)) {  // check if it is a valid RGB color (e.g, #a2ff4b or #a0f)
                                    color = color.substr(1);              // strip the # prefix
                                }
                                if (!/^[0-9a-f]{6}$/i.test(color)) color = defaultGroupColor;
                                pattern = 'none';
                                if (typeof l[2] !== 'undefined') {   // read an optional pattern
                                    p = l[2].trim();
                                    j = pattern_names.filter(function (v) {
                                        return v.id === p;
                                    })[0];
                                    if (typeof j !== 'undefined') pattern = p;
                                }
                                if (name === 'Default') {
                                    g[0].color = color;
                                    g[0].pattern = 'none';
                                } else {
                                    g.push({recid: name, color: color, pattern: pattern});
                                }
                                loadedGroups += 1;
                            }
                        }
                    }
                }
            }
            if (loadedGroups > 0) {
                defaultGroupColor = g[0].color;

                /*
                 * Some groups were added, besides the default one, so update w2ui.groups
                 */

                w2ui.groups.clear();
                w2ui.groups.add(g);

                /*
                 * Now check if haplotype list is already defined
                 * and clean any classification made
                 */

                if (w2ui.haplotypes.records.length > 0) {
                    var oldGroup;
                    for (i = 0; i < w2ui.haplotypes.records.length; i++) {
                        oldGroup = w2ui.haplotypes.records[i].group;
                        w2ui.haplotypes.records[i].group = 'Default';
                        w2ui.haplotypes.records[i].color = g[0].color;
                        classify(i, 'Default', oldGroup);
                    }
                    w2ui.haplotypes.refresh();
                }

                /*
                 * If SVG is already set, reset fill patterns
                 */

                if (svg) {

                    /*
                     * Remove any pattern definition from the SVG
                     */

                    $('pattern').remove();
                    for (i = 0; i < w2ui.groups.records.length; i++) {
                        if (w2ui.groups.records[i].pattern !== 'none') {
                            createPattern(w2ui.groups.records[i].pattern, w2ui.groups.records[i].color);
                        }
                    }
                }
                if (hasMeta) {
                    g.forEach(function (record) {
                        syncMetaGroupColor(record.recid, record.color);
                    });
                    syncAllMetaHaplotypeGroups(false);
                    updateSVG();
                    refreshMetaLegend();
                }

            } else {
                w2alert('This seems not to be a formatted "Group" file!<br>' + '(CSV text file with group names and colors   <br>' + 'separated by a semicolon. Please hit the Help button.', 'No groups loaded!');
            }

            /*
             * clear input field so that file can be reopened!
             */

            fileInput.value = "";
        };

        if (w2ui.groups.records.length > 1) {

            /*
             * Groups already loaded! Override?
             */

            w2confirm('Old list will be deleted! If some haplotypes have<br>' + 'already been associated with groups (colors) they<br>' + 'may revert to default group or become associated <br>' + 'with a different group                           <p>' + 'Load the new list?', 'Replace active group\'s list?')
                .yes(function () {
                    reader.readAsText(input.files[0]);
                });
        } else {
            reader.readAsText(input.files[0]);
        }
    }


    /*
     * Reads a traitconf file (semicolon-delimited, no header row).
     * Each line has the format: seqname;value
     * where seqname is a sequence ID and value is a continuous time trait.
     * Updates matching haplotype time values and rebuilds timeProportions.
     * In standalone mode the Traits grid gets one generic trait summary; when
     * NetST metadata is active its named trait catalog always takes precedence.
     */
    function loadTraits(e) {

        var input = e.target;

        if (input.files.length !== 1) return;

        var reader = new FileReader();

        reader.onload = function () {
            var text = reader.result;
            var lines = text.split('\n');

            // Collect seqname → value pairs from the file
            var traitMap = {};
            for (var i = 0; i < lines.length; i++) {
                var line = lines[i].trim();
                if (line === '') continue;
                var parts = line.split(';');
                if (parts.length < 2) continue;
                var seqname = parts[0].trim();
                var value = parseFloat(parts[1].trim());
                if (seqname === '' || isNaN(value)) continue;
                // Normalize seqname to match how haplotype recids are normalized in loadGraph
                seqname = seqname.replace(/[\W]/g, "_");
                if (/^\d+$/.test(seqname[0])) seqname = 'L' + seqname;
                traitMap[seqname] = value;
            }

            // Compute minTime/maxTime by matching seqnames directly against nodeList names.
            // Each node's name field contains one or more sequence names joined by '\n'.
            minTime = Number.POSITIVE_INFINITY;
            maxTime = Number.NEGATIVE_INFINITY;
            nodeList.forEach(function (node) {
                if (node.nodestyle !== 1) return;
                var seqs = node.name.split('\n').filter(function (s) {
                    return s.trim() !== '';
                });
                seqs.forEach(function (seq) {
                    var t = traitMap[seq.trim()];
                    if (t !== undefined) {
                        minTime = Math.min(minTime, t);
                        maxTime = Math.max(maxTime, t);
                    }
                });
            });

            // Determine style and build color scale.
            // Mirror time/timecolor onto haplotype records for classic rendering.
            var colorScale = null;
            if (minTime !== maxTime) {
                styleid = 0;
                colorScale = d3.scale.linear()
                    .domain([minTime, maxTime])
                    .range([8, 247]);
            } else {
                styleid = 1;
            }

            // Update haplotype records with time and timecolor values.
            w2ui.haplotypes.records.forEach(function (haplo) {
                if (Object.prototype.hasOwnProperty.call(traitMap, haplo.recid)) {
                    haplo.time = traitMap[haplo.recid];
                    if (haplo.nodestyle && colorScale) {
                        var gv = Math.round(colorScale(maxTime + minTime - haplo.time));
                        haplo.timecolor = gv.toString(16).padStart(2, '0');
                    }
                }
            });

            // Rebuild timeProportions by matching each node's sequence names against traitMap.
            // Each matched sequence contributes count=1 to its time bucket.
            nodeList.forEach(function (node) {
                node.timeProportions = [];
                if (node.nodestyle !== 1) return;
                var seqs = node.name.split('\n').filter(function (s) {
                    return s.trim() !== '';
                });
                seqs.forEach(function (seq) {
                    var t = traitMap[seq.trim()];
                    if (t === undefined) return; // seqname not in traitconf
                    var existing = node.timeProportions.find(function (tp) {
                        return tp.time === t;
                    });
                    if (existing) {
                        existing.value += 1;
                    } else {
                        var tc = colorScale
                            ? Math.round(colorScale(maxTime + minTime - t)).toString(16).padStart(2, '0')
                            : 'ff';
                        node.timeProportions.push({
                            time: t,
                            value: 1,
                            timecolor: tc,
                            radius: node.radius
                        });
                    }
                });
                // Continuous sectors must follow numeric order around the ring,
                // independent of the original sample order in the haplotype.
                node.timeProportions.sort(function (a, b) {
                    return Number(a.time) - Number(b.time);
                });
            });

            hasTrait = true;
            if (svg) updateSVG();
        };

        /*
         * Capture the embedded or user-provided file reference.
         */
        var file = input.files[0];
        reader.readAsText(file);
    }


    /*
    * Reads a CSV file with haplotype names and groups
    */

    function loadHaplotypes(e) {

        var input = e.target;

        /*
         * Read only one file, no more, no less
         */

        if (input.files.length !== 1) return;

        var fileInput = document.getElementById('loadHaplotypes');

        var reader = new FileReader();

        reader.onload = function () {

            var text = reader.result;
            var lines = text.split('\n');
            var line, l, name, displayName, group, seq2hap;
            var i, h = [];

            /*
             * Detect column count from the first non-empty data line.
             * Accept 2-col (seq;group) or 3-col (seq;group;hapname) formats.
             */
            var detectedColumns = 0;
            for (i = 0; i < lines.length; i++) {
                line = lines[i].trim();
                if (line !== '') {
                    l = line.split(";");
                    if (l.length === 2 || l.length === 3) {
                        detectedColumns = l.length;
                        break;
                    }
                }
            }

            for (i = 0; i < lines.length; i++) {
                line = lines[i].trim();
                if (line !== '') {

                    l = line.split(";");

                    /*
                     * Accept lines with two fields (seq;group) or three fields (seq;group;hapname).
                     */

                    if (l.length === 2 || l.length === 3) {
                            displayName = l[0].trim();
                            name = displayName;
                        if (name !== '') {

                            /*
                             * Standardize the string (only alpha/numbers and _ allowed).
                             * If name starts with a digit, prepend 'L' as loadGraph does.
                             */

                            name = name.replace(/[\W]/g, "_");

                            if (/^\d+$/.test(name[0])) name = 'L' + name;

                            /*
                             * Read second column (group) and optional third column (hap name).
                             */

                            group = l[1].trim();
                            seq2hap = (l.length === 3) ? l[2].trim() : '';
                            if (group !== "") h.push({
                                label: name,
                                displayName: displayName,
                                group: group,
                                seq2hap: seq2hap
                            });
                        }
                    }
                }
            }

            /*
             * Check if a list of haplotypes <-> groups was created
             */

            if (h.length > 0) {

                /*
                 * Record column format for the current hapconf file.
                 */
                hapconfColumns = detectedColumns;

                /*
                 * Iterate through all haplotypes in the list, check if they exist
                 * in the haplotype grid and change their group accordingly. Check
                 * also if the group is defined in the group's list. Otherwise,
                 * don't change anything (keep the default group)
                 */

                var hap, grp, ogrp;
                for (i = 0; i < h.length; i++) {

                    hap = w2ui.haplotypes.find({recid: h[i].label}, true)[0];
                    grp = w2ui.groups.find({recid: h[i].group}, true)[0];

                    if ((typeof hap !== 'undefined') && (typeof grp !== 'undefined')) {

                        ogrp = w2ui.haplotypes.records[hap].group;
                        if (typeof ogrp === 'undefined') ogrp = 'Default';

                        w2ui.haplotypes.records[hap].group = h[i].group;
                        w2ui.haplotypes.records[hap].color = w2ui.groups.records[grp].color;
                        w2ui.haplotypes.records[hap].seq2hap = h[i].seq2hap;
                        w2ui.haplotypes.records[hap].displayName = h[i].displayName;

                        classify(hap, h[i].group, ogrp);
                    }
                }

                /*
                 * For 3-column hapconf, populate node.hap by matching each node's
                 * first sequence name against the loaded seq→hapname mapping.
                 * For 2-column hapconf, clear any previously set node.hap values.
                 */
                if (hapconfColumns === 3) {
                    var seq2hapMap = {};
                    for (i = 0; i < h.length; i++) {
                        seq2hapMap[h[i].label] = h[i].seq2hap;
                    }
                    nodeList.forEach(function (node) {
                        if (node.nodestyle === 1) {
                            var firstName = node.name.split('\n')[0].trim();
                            node.hap = seq2hapMap[firstName] || null;
                        }
                    });
                } else {
                    nodeList.forEach(function (node) {
                        node.hap = null;
                    });
                }

                hapconfLoaded = true;

                /*
                 * Enable the Haplotype toolbar button only when hap names are available (3-col).
                 */
                if (hapconfColumns === 3) {
                    w2ui.Layout_main_toolbar.enable('btn-haplotype');
                } else {
                    seqHapFlag = false;
                    labelNode = {};
                    w2ui.Layout_main_toolbar.uncheck('btn-haplotype');
                    w2ui.Layout_main_toolbar.disable('btn-haplotype');
                }

                if (hasMeta) syncAllMetaHaplotypeGroups(false);
                updateSVG();
                if (hasMeta) refreshMetaLegend();
                w2ui.haplotypes.refresh();
            } else {
                w2alert('This seems not to be a formatted "Haplotype" file!<br>' + '(CSV text file with haplotype and group names     <br>' + 'separated by a semicolon. Please hit the Help button.', 'No haplotypes loaded!');
            }

            /*
             * clear input field so that file can be reopened!
             */

            fileInput.value = "";
        };

        if (w2ui.groups.records.length > 1) {  //Groups already loaded! Override?
            w2confirm('Colors will be replaced in the haplotype list! If<br>' + 'any color has already been assigned they will be<br>' + 'overriden! Load the colors\' list, anyway?       <br>', 'Replace active group\'s list?').yes(function () {
                reader.readAsText(input.files[0]);
            });
        } else {
            reader.readAsText(input.files[0]);
        }
    }

    function saveGroups() {
        if (filesave) {
            var label, color, pattern;
            var list = [];

            /*
             * Group list exists
             */

            if (w2ui.groups.records.length > 0) {
                for (var i = 1; i < w2ui.groups.records.length; i++) {
                    label = w2ui.groups.records[i].recid;
                    color = w2ui.groups.records[i].color;
                    pattern = w2ui.groups.records[i].pattern;
                    list.push(label + ';#' + color + ';' + pattern + '\n');
                }
                var blob = new Blob(list, {type: "text/plain;charset=utf-8"}, {endings: "native"});
                saveAs(blob, "groups.csv");
            }
        } else {
            w2alert('FileSaver.js is not supported! Use a modern browser...<br>' + 'FileSaver.js is supported by Firefox 20+, Chrome, Chrome<br>' + 'for Android, IE 10+, Opera 15+ and Safari 6.1+', 'FileSave.js is unsupported!');
        }
    }


    /*
     * Toggle display of the seq2hap label on each node in the SVG.
     * The haplogroup→seq2hap mapping is built once and cached in each node object.
     */
    function insertHaplotype() {
        seqHapFlag = !seqHapFlag;
        // A toolbar action means "all on" or "all off", so discard prior
        // single-node exceptions.  Info can add fresh per-node overrides.
        labelNode = {};
        updateSVG();
        if (activeInfoNode && refreshActiveNodeInfo) refreshActiveNodeInfo(activeInfoNode);
    }

    function escapeHtml(value) {
        return String(value === undefined || value === null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function nodeSequenceEntries(node) {
        var ids = String(node && node.name ? node.name : '').split('\n').filter(function (value) {
            return value.trim() !== '';
        });
        return ids.map(function (id) {
            var record = null;
            if (w2ui.haplotypes) {
                var found = w2ui.haplotypes.find({recid: id}, true);
                if (found && found.length > 0) record = w2ui.haplotypes.records[found[0]];
            }
            return {id: id, label: record && record.displayName ? record.displayName : id};
        });
    }

    function getNodeNameIdLabel(node) {
        var entries = nodeSequenceEntries(node);
        if (!entries.length) return '';
        var selected = nodeNameId[node.name];
        if (selected && entries.some(function (entry) { return entry.label === selected; })) {
            return selected;
        }
        nodeNameId[node.name] = entries[0].label;
        return entries[0].label;
    }

    function insertNameId() {
        nameIdFlag = !nameIdFlag;
        nameIdNode = {};
        updateSVG();
        if (activeInfoNode && refreshActiveNodeInfo) refreshActiveNodeInfo(activeInfoNode);
    }

    /*
     * Toggle display of the mutation-change count on each link in the SVG.
     */
    function insertDistance() {
        distanceFlag = !distanceFlag;
        updateSVG();
    }

    function saveHaplotypes() {
        if (filesave) {
            var label, group, seq2hap;
            var list = [];

            /*
             * Haplotype list has been loaded
             */

            if (w2ui.haplotypes.records.length > 0) {
                for (var i = 0; i < w2ui.haplotypes.records.length; i++) {
                    label = w2ui.haplotypes.records[i].recid;
                    group = w2ui.haplotypes.records[i].group;
                    seq2hap = w2ui.haplotypes.records[i].seq2hap;
                    list.push(label + ';' + group + ';' + seq2hap + '\n');
                }
                var blob = new Blob(list, {type: "text/plain;charset=utf-8"}, {endings: "native"});
                saveAs(blob, "haplotypes.csv");
            }
        } else {
            w2alert('FileSaver.js is not supported! Use a modern browser...<br>' + 'FileSaver.js is supported by Firefox 20+, Chrome, Chrome<br>' + 'for Android, IE 10+, Opera 15+ and Safari 6.1+', 'FileSave.js is unsupported!');
        }
    }

    function serializedNetworkSVG() {
        var source = document.getElementById('SVG');
        if (!source) return null;

        var clone = source.cloneNode(true);

        // Frame the *entire* drawing — every node, link, label and legend —
        // rather than the visible panel, so nothing is cropped no matter how the
        // user has panned or zoomed. getBBox on the root <svg> returns the union
        // of all rendered geometry (in the svg's own coordinate system, i.e. at
        // the current zoom), including content that lies outside the viewport.
        var box = null;
        try {
            box = source.getBBox();
        } catch (e) {
            box = null;
        }
        var pad = 24;
        var minX, minY, width, height;
        if (box && isFinite(box.width) && isFinite(box.height)
            && box.width > 0 && box.height > 0) {
            minX = box.x - pad;
            minY = box.y - pad;
            width = Math.max(1, Math.round(box.width + 2 * pad));
            height = Math.max(1, Math.round(box.height + 2 * pad));
        } else {
            // Nothing measurable (empty graph) — fall back to the visible panel.
            var rect = source.getBoundingClientRect();
            minX = 0;
            minY = 0;
            width = Math.max(1, Math.round(rect.width || $('#gview').width() || 1));
            height = Math.max(1, Math.round(rect.height || $('#gview').height() || 1));
        }

        clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        clone.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
        clone.setAttribute('viewBox', minX + ' ' + minY + ' ' + width + ' ' + height);
        clone.setAttribute('width', width);
        clone.setAttribute('height', height);
        clone.setAttribute('preserveAspectRatio', 'xMidYMid meet');

        var bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bg.setAttribute('x', minX);
        bg.setAttribute('y', minY);
        bg.setAttribute('width', width);
        bg.setAttribute('height', height);
        bg.setAttribute('fill', '#FFFFFF');
        clone.insertBefore(bg, clone.firstChild);

        return {
            markup: '<?xml version="1.0" encoding="UTF-8"?>\n' +
                new XMLSerializer().serializeToString(clone),
            width: width,
            height: height
        };
    }

    function detachedJSON(value) {
        return JSON.parse(JSON.stringify(value));
    }

    function exportProjectViewState() {
        if (!nodeList || nodeList.length === 0) return null;
        return {
            version: 1,
            captured_at: new Date().toISOString(),
            layout: {
                link_distance: Number(lnkdist),
                link_strength: Number(lnkstre),
                friction: Number(frict),
                charge: Number(chrg),
                gravity: Number(grav)
            },
            style: {
                node_radius: Number(standardRadius),
                node_line_width: Number(nodeLineWidth),
                edge_line_width: Number(edgeLineWidth),
                edge_weight_scale: Number(edgeWeightScale),
                ring_line_width: Number(metaRingLineWidth),
                ring_ratio: Number(metaRingRatio),
                ring_scales: metaRingScales.slice(),
                text_offset: Number(textOffset),
                haplotype_font_size: Number(haplotypeFontSize),
                name_id_font_size: Number(nameIdFontSize)
            },
            toggles: {
                legend: legend === 1,
                haplotype_labels: !!seqHapFlag,
                name_id_labels: !!nameIdFlag,
                distance_labels: !!distanceFlag,
                edge_weight: !!edgeWeightFlag
            },
            legend_transforms: $('.legend').map(function () {
                return $(this).attr('transform') || '';
            }).get(),
            zoom: zoom ? {
                scale: Number(zoom.scale()),
                translate: zoom.translate().map(Number)
            } : null,
            nodes: nodeList.map(function (item) {
                return {
                    id: item.id,
                    name: item.name,
                    x: Number(item.x),
                    y: Number(item.y),
                    px: Number(item.px),
                    py: Number(item.py),
                    fixed: !!item.fixed
                };
            }),
            visible_link_ids: linkList.map(function (item) { return item.id; }),
            label_node: detachedJSON(labelNode),
            name_id_node: detachedJSON(nameIdNode),
            node_name_id: detachedJSON(nodeNameId),
            node_text_layout: detachedJSON(nodeTextLayout),
            label_link: detachedJSON(labelLink),
            highlight_nodes: highlightNode.slice(),
            highlight_links: highlightLink.slice(),
            meta_config: metaConfig ? detachedJSON(metaConfig) : null
        };
    }

    function applyProjectViewState(state) {
        if (!state || state.version !== 1 || !nodeList || nodeList.length === 0) {
            return false;
        }
        if (force) force.stop();

        var savedNodes = {};
        (state.nodes || []).forEach(function (item) {
            savedNodes[String(item.id)] = item;
        });
        if (Object.keys(savedNodes).length > 0) {
            nodeList = nodeList.filter(function (item) {
                return Object.prototype.hasOwnProperty.call(savedNodes, String(item.id));
            });
        }

        var visibleLinks = {};
        (state.visible_link_ids || []).forEach(function (id) {
            visibleLinks[String(id)] = true;
        });
        if (state.visible_link_ids) {
            linkList = linkList.filter(function (item) {
                return !!visibleLinks[String(item.id)];
            });
            var visiblePairs = {};
            linkList.forEach(function (item) {
                var a = String(item.source.id), b = String(item.target.id);
                visiblePairs[a + '\u0000' + b] = true;
                visiblePairs[b + '\u0000' + a] = true;
            });
            edgeList = edgeList.filter(function (item) {
                return !!visiblePairs[String(item.source) + '\u0000' + String(item.target)];
            });
        }

        var style = state.style || {};
        var savedRadius = Number(style.node_radius);
        if (isFinite(savedRadius) && savedRadius > 0 && savedRadius !== standardRadius) {
            var radiusScale = savedRadius / standardRadius;
            standardRadius = savedRadius;
            nodeList.forEach(function (item) {
                if (item.nodestyle !== 1) return;
                item.radius *= radiusScale;
                (item.proportions || []).forEach(function (part) {
                    part.radius *= radiusScale;
                });
                (item.timeProportions || []).forEach(function (part) {
                    if (part.radius) part.radius *= radiusScale;
                });
            });
        }
        function finiteOr(value, fallback) {
            var number = Number(value);
            return isFinite(number) ? number : fallback;
        }
        nodeLineWidth = finiteOr(style.node_line_width, nodeLineWidth);
        edgeLineWidth = finiteOr(style.edge_line_width, edgeLineWidth);
        edgeWeightScale = finiteOr(style.edge_weight_scale, edgeWeightScale);
        metaRingLineWidth = finiteOr(style.ring_line_width, metaRingLineWidth);
        metaRingRatio = finiteOr(style.ring_ratio, metaRingRatio);
        metaRingScales = Array.isArray(style.ring_scales)
            ? style.ring_scales.map(Number) : metaRingScales;
        textOffset = finiteOr(style.text_offset, textOffset);
        haplotypeFontSize = finiteOr(style.haplotype_font_size, haplotypeFontSize);
        nameIdFontSize = finiteOr(style.name_id_font_size, nameIdFontSize);

        var layout = state.layout || {};
        lnkdist = finiteOr(layout.link_distance, lnkdist);
        lnkstre = finiteOr(layout.link_strength, lnkstre);
        frict = finiteOr(layout.friction, frict);
        chrg = finiteOr(layout.charge, chrg);
        grav = finiteOr(layout.gravity, grav);

        var toggles = state.toggles || {};
        var restoreLegend = !!toggles.legend;
        legend = 0;
        seqHapFlag = !!toggles.haplotype_labels;
        nameIdFlag = !!toggles.name_id_labels;
        distanceFlag = !!toggles.distance_labels;
        edgeWeightFlag = !!toggles.edge_weight;
        labelNode = detachedJSON(state.label_node || {});
        nameIdNode = detachedJSON(state.name_id_node || {});
        nodeNameId = detachedJSON(state.node_name_id || {});
        nodeTextLayout = detachedJSON(state.node_text_layout || {});
        labelLink = detachedJSON(state.label_link || {});
        highlightNode = (state.highlight_nodes || []).slice();
        highlightLink = (state.highlight_links || []).slice();

        if (state.meta_config) {
            pendingMetaConfig = detachedJSON(state.meta_config);
            applyMetaConfig();
        }
        nodeList.forEach(function (item) {
            var saved = savedNodes[String(item.id)];
            if (!saved) return;
            item.x = finiteOr(saved.x, item.x);
            item.y = finiteOr(saved.y, item.y);
            item.px = finiteOr(saved.px, item.x);
            item.py = finiteOr(saved.py, item.y);
            item.fixed = !!saved.fixed;
        });

        if (force) {
            force.nodes(nodeList).links(linkList)
                .linkDistance(function (item) { return item.ldist * lnkdist; })
                .linkStrength(lnkstre).friction(frict).gravity(grav)
                .charge(function (item) { return item ? item.radius * chrg : chrg; });
        }
        updateSVG();
        $('.legend').remove();
        legend = 0;
        if (restoreLegend) {
            insertLegend();
            var transforms = state.legend_transforms || [];
            $('.legend').each(function (index) {
                if (transforms[index]) $(this).attr('transform', transforms[index]);
            });
        }
        if (zoom && state.zoom) {
            var scale = finiteOr(state.zoom.scale, zoom.scale());
            var translate = Array.isArray(state.zoom.translate)
                ? state.zoom.translate.map(Number) : zoom.translate();
            zoom.scale(scale).translate(translate);
            svg.attr("transform", "translate(" + translate + ")scale(" + scale + ")");
        }
        if (force) force.stop();
        return true;
    }

    function saveImage(format) {
        if (!filesave) {
            w2alert('FileSaver.js is not supported! Use a modern browser...',
                'Image export is unsupported');
            return;
        }
        var imageFormat = String(format || 'svg').toLowerCase();
        if (imageFormat === 'jpeg') imageFormat = 'jpg';
        if (['svg', 'png', 'jpg', 'pdf'].indexOf(imageFormat) === -1) {
            w2alert('Unsupported image format: ' + imageFormat, 'Image export failed');
            return;
        }

        if (force) force.stop();
        window._lastNetstExportState = exportProjectViewState();
        var exported = serializedNetworkSVG();
        if (!exported) {
            w2alert('Build or load a network before exporting an image.',
                'No network to export');
            return;
        }
        window._lastNetstExportState.export = {
            format: imageFormat,
            width: exported.width,
            height: exported.height,
            raster_scale: 1,
            jpeg_quality: imageFormat === 'jpg' ? 0.95 : null
        };
        var svgBlob = new Blob(
            [exported.markup], {type: 'image/svg+xml;charset=utf-8'});
        if (imageFormat === 'svg') {
            saveAs(svgBlob, 'network.svg');
            return;
        }

        if (imageFormat === 'pdf') {
            window._pdfSvgPayload = {
                markup: exported.markup,
                width: exported.width,
                height: exported.height
            };
            var triggerBlob = new Blob(['pdf'], {type: 'application/octet-stream'});
            saveAs(triggerBlob, 'network.netst-pdf-trigger');
            return;
        }

        var objectUrl = URL.createObjectURL(svgBlob);
        var rasterImage = new Image();
        rasterImage.onload = function () {
            var scale = 3;
            var maxSide = 12000;
            var longest = Math.max(exported.width, exported.height);
            if (longest * scale > maxSide) {
                scale = Math.max(0.5, maxSide / longest);
            }
            if (window._lastNetstExportState && window._lastNetstExportState.export) {
                window._lastNetstExportState.export.raster_scale = scale;
            }
            var canvas = document.createElement('canvas');
            canvas.width = Math.round(exported.width * scale);
            canvas.height = Math.round(exported.height * scale);
            var context = canvas.getContext('2d');
            if (imageFormat === 'jpg') {
                context.fillStyle = '#FFFFFF';
                context.fillRect(0, 0, canvas.width, canvas.height);
            }
            context.setTransform(scale, 0, 0, scale, 0, 0);
            context.drawImage(rasterImage, 0, 0, exported.width, exported.height);
            URL.revokeObjectURL(objectUrl);
            var mime = imageFormat === 'jpg' ? 'image/jpeg' : 'image/png';
            canvas.toBlob(function (blob) {
                if (!blob) {
                    w2alert('The browser could not create the image file.',
                        'Image export failed');
                    return;
                }
                saveAs(blob, 'network.' + imageFormat);
            }, mime, imageFormat === 'jpg' ? 0.95 : undefined);
        };
        rasterImage.onerror = function () {
            URL.revokeObjectURL(objectUrl);
            w2alert('The SVG could not be rendered as a raster image.',
                'Image export failed');
        };
        rasterImage.src = objectUrl;
    }

    function zoomByFactor(factor) {
        if (!zoom) return;
        var scale = zoom.scale();
        var extent = zoom.scaleExtent();
        var newScale = scale * factor;
        var w = $('#gview').width();
        var h = $('#gview').height();
        if (extent[0] <= newScale && newScale <= extent[1]) {
            var t = zoom.translate();
            var c = [w / 2, h / 2];
            zoom
                .scale(newScale)
                .translate([c[0] + (t[0] - c[0]) / scale * newScale, c[1] + (t[1] - c[1]) / scale * newScale])
                .event(svg.transition().duration(350));
        }
    }

    function pushUndoSnapshot() {
        undoStack.push({
            nodes: JSON.parse(JSON.stringify(nodeList.map(function (n) {
                return {
                    id: n.id, name: n.name, radius: n.radius, nodestyle: n.nodestyle,
                    proportions: n.proportions, timeProportions: n.timeProportions,
                    metaRings: n.metaRings, hap: n.hap, x: n.x, y: n.y
                };
            }))),
            edges: JSON.parse(JSON.stringify(edgeList))
        });
        if (undoStack.length > 20) undoStack.shift();
        w2ui.Layout_main_toolbar.enable('btn-undo');
    }

    function undoDelete() {
        if (undoStack.length === 0) return;
        var snapshot = undoStack.pop();
        if (undoStack.length === 0) w2ui.Layout_main_toolbar.disable('btn-undo');
        nodeList.length = 0;
        edgeList.length = 0;
        snapshot.nodes.forEach(function (sn) {
            nodeList.push(sn);
        });
        snapshot.edges.forEach(function (se) {
            edgeList.push(se);
        });
        linkList.length = 0;
        for (var i = 0; i < edgeList.length; i++) {
            var pair = nodeList.filter(function (e) {
                return (e.id === edgeList[i].source) || (e.id === edgeList[i].target);
            });
            if (pair.length === 2) linkList.push({
                source: pair[0], target: pair[1],
                id: "Link_" + pair[0].id + "-" + pair[1].id,
                ldist: pair[0].radius + pair[1].radius + defaultLinkDistance + defaultDistance,
                changes: edgeList[i].changes
            });
        }
        if (hasMeta) {
            for (var mi = 0; mi < nodeList.length; mi++) {
                nodeList[mi].metaSegments = computeMetaSegments(nodeList[mi]);
            }
        }
        updateSVG();
    }

    function toggleEdgeWeight() {
        edgeWeightFlag = !edgeWeightFlag;
        updateSVG();
    }

    function searchNode(query) {
        if (!query || !nodeList || nodeList.length === 0) return;
        query = query.trim().toLowerCase();
        var found = null;
        for (var i = 0; i < nodeList.length; i++) {
            var n = nodeList[i];
            if (n.nodestyle !== 1) continue;
            var names = n.name ? n.name.split('\n') : [];
            for (var j = 0; j < names.length; j++) {
                if (names[j].trim().toLowerCase().indexOf(query) >= 0) {
                    found = n;
                    break;
                }
            }
            if (found) break;
            if (n.hap && n.hap.toLowerCase().indexOf(query) >= 0) {
                found = n;
                break;
            }
        }
        if (!found) {
            w2alert('No node found matching "' + query.replace(/</g, '&lt;') + '"', 'Search');
            return;
        }
        highlightNode = [found.name];
        updateSVG();
        if (zoom && found.x !== undefined && found.y !== undefined) {
            var w = $('#gview').width();
            var h = $('#gview').height();
            var s = zoom.scale();
            var tx = w / 2 - found.x * s;
            var ty = h / 2 - found.y * s;
            zoom.translate([tx, ty])
                .event(svg.transition().duration(500));
        }
        if (typeof clickNode === 'function') {
            var savedDeleteNode = deletenode;
            deletenode = false;
            clickNode(found);
            deletenode = savedDeleteNode;
        }
    }

    function svgStart() {

        var massFactor = 0; // reserved for future node-mass scaling; currently unused
        lnkdist = defaultLinkDistance;
        lnkstre = defaultLinkStrength;
        frict = defaultFriction;
        chrg = defaultCharge;
        // Do not mess with this
        // var chrgdist = Infinity;
        grav = defaultGravity;

        /*
         * clear linkList if not empty
         */

        linkList = [];

        /*
         * arry of nodes is in global var 'nodeList'
         * array of edges is in global variable 'edgeList'
         *
         * Sort nodes based on radius size (frequency) so that smaller nodes
         * are added last to the list and will be on top of the bigger
         * ones, thus avoiding being hidden by the latter upon draw
         * */

        nodeList.sort(function comp(a, b) {
            var r = (a.radius < b.radius) ? 1 : (a.radius > b.radius) ? -1 : 0;
            return r;
        });

        /* The 'edges' array has source/target node pairs. However, since nodeList was
         * sorted, these pairs are not synced with the index of the nodes array anymore.
         * We build a 'linkList' array by pushing from the nodeList array the 'target'
         * and 'source' nodes and passing them as objects for the linkList. We also
         * use the radius of the nodes to set an ideal link distance which is equal to the
         * sum of their radii, plus the default distance between two nodes with radii = 1
         */

        var pair;

        for (var i = 0; i < edgeList.length; i++) {
            pair = nodeList.filter(function (e) {
                return (e.id === edgeList[i].source) || (e.id === edgeList[i].target);
            });
            if (pair.length === 2) linkList.push({
                source: pair[0],
                target: pair[1],
                id: "Link_" + pair[0].id + "-" + pair[1].id,
                ldist: pair[0].radius + pair[1].radius + lnkdist + defaultDistance,
                changes: edgeList[i].changes
            });
        }

        /*
         * Redraw elements on zoom/pan
         */

        zoom = d3.behavior.zoom().on("zoom", zoom_redraw);

        function zoom_redraw() {
            svg.attr("transform", "translate(" + zoom.translate() + ")" + "scale(" + zoom.scale() + ")");
        }

        /*
         * Compute 'view' width and height
         */

        var w = $('#gview').width();
        var h = $('#gview').height();

        /*
         * Remove paper advertisement from main DIV
         */

        $('#gview').empty();

        /*
         * Define the main svg element
         */

        svg = d3.select('#gview')
            .append('svg')
            .attr('id', 'SVG')
            .attr("width", "100%")
            .attr("height", "100%")
            .attr("viewBox", "0 0 " + w + " " + h)
            .attr("preserveAspectRatio", "xMidYMid meet")
            //.call(d3.behavior.zoom().on("zoom", zoom_redraw))
            .call(zoom)
            .append('g');

        /*
         * Define a baseline force layout
         */

        force = d3.layout.force()
            .charge(function (d) {
                if (d) return d.radius * chrg; else return chrg;
            })
            .linkDistance(function (d) {
                if (d) return d.ldist * lnkdist; else return lnkdist;
            })
            .gravity(grav)
            .friction(frict)
            .linkStrength(lnkstre)
            .chargeDistance(Infinity)
            .size([w, h])
            .on('end', function () {
                $('#stop').prop('disabled', true);
                $('#start').prop('disabled', false);
            })
            .on('start', function () {
                $('#stop').prop('disabled', false);
                $('#start').prop('disabled', true);
            });

        /*
         * Define a layout for pie charts
         */

        pie = d3.layout.pie()
            .sort(null)
            .value(function (d) {
                return d.value;
            });

        subPie = d3.layout.pie()
            .sort(function (a, b) {
                return a.time - b.time;  // sort ascending by time
            })
            .value(function (d) {
                return d.value;
            });

        /*
         * Define an arc
         */

        sector = d3.svg.arc()
            .outerRadius(function (d) {
                return d.data.radius;
            })
            .innerRadius(0);

        sectorOuter = d3.svg.arc()
            .outerRadius(function (d) {
                return d.data.radius * outerRadiusCoeff;
            })
            .innerRadius(function (d) {
                return d.data.radius * innerRadiusCoeff;
            });

        sectorSmall = d3.svg.arc()
            .outerRadius(function (d) {
                return d.data.radius * innerRadiusCoeff;
            })
            .innerRadius(0);

        sectorNull = d3.svg.arc()
            .outerRadius(0)
            .innerRadius(0);

        // Arc generator for NetST metadata rings; each datum carries its own
        // inner/outer radius and start/end angle (see computeMetaSegments).
        metaArc = d3.svg.arc()
            .innerRadius(function (d) {
                return d.inner;
            })
            .outerRadius(function (d) {
                return d.outer;
            })
            .startAngle(function (d) {
                return d.startAngle;
            })
            .endAngle(function (d) {
                return d.endAngle;
            });
        /*
         * Create SVG patterns for the groups defined (except for default group 0)
         */

        defs = svg.append("defs");

        for (var i = 1; i < w2ui.groups.records.length; i++) {
            if (w2ui.groups.records[i].pattern !== 'none') createPattern(w2ui.groups.records[i].pattern, w2ui.groups.records[i].color);
        }

        /*
         * Define what to do in each iteration of the force layout tick.
         * Updates link endpoints and node positions on the SVG.
         */

        force.on("tick", updateSVGPositions);

        /*
         * Define costum drag
         */

        drag = force.drag().on("dragstart", function (d) {
            d3.event.sourceEvent.stopPropagation();
        });
        force.stop();
        refreshActiveNodeInfo = showNodeInfo;
        /*
         * Delete a selected node
         */

        clickNode = function (e) {
            if (deletenode) {
                if (activeInfoNode === e) activeInfoNode = null;
                pushUndoSnapshot();
                nodeList.splice(nodeList.indexOf(e), 1);
                edgeList = edgeList.filter(function (edge) {
                    return edge.source !== e.id && edge.target !== e.id;
                });
                var toSplice = linkList.filter(function (l) {
                    return (l.source === e) || (l.target === e);
                });
                toSplice.forEach(function (l) {
                    linkList.splice(linkList.indexOf(l), 1);
                });
                updateSVG();
            } else {
                activeInfoNode = e;
                showNodeInfo(e);
            }
        };

        /*
         * Show node information in the Node Info right panel.
         */
        function showNodeInfo(node) {
            var isHaplotype = node.nodestyle === 1 && !isIntermediateNode(node);
            var haploLabel = getNodeDisplayLabel(node);
            var nameEntries = nodeSequenceEntries(node);
            var names = nameEntries.map(function (entry) { return entry.id; });

            var html = '<div style="padding:10px;">';
            // Top: haplotype label
            html += '<div style="font-weight:bold; font-size:16px; color:#2d4a6a; border-bottom:2px solid #2d4a6a; padding-bottom:6px; margin-bottom:10px;">' + haploLabel + '</div>';

            html += '<table style="width:100%; font-size:12px; border-collapse:collapse;">';
            html += '<tr><td style="color:#666; padding:3px 0; white-space:nowrap; width:70px;">ID:</td>' +
                '<td style="padding:3px 4px;">' + node.id + '</td></tr>';
            html += '<tr><td style="color:#666; padding:3px 0; white-space:nowrap;">Type:</td>' +
                '<td style="padding:3px 4px;">' + (isHaplotype ? 'Haplotype' : 'Transition') + '</td></tr>';
            if (isHaplotype && hapconfColumns === 3 && node.hap) {
                html += '<tr><td style="color:#666; padding:3px 0; white-space:nowrap;">Haplotype:</td>' +
                    '<td style="padding:3px 4px; font-weight:bold;">' + node.hap + '</td></tr>';
            }

            if (isHaplotype) {
                var freq = 0;
                node.proportions.forEach(function (p) {
                    freq += p.value;
                });
                html += '<tr><td style="color:#666; padding:3px 0; white-space:nowrap;">Frequency:</td>' +
                    '<td style="padding:3px 4px;">' + freq + '</td></tr>';

                var activeGroups = node.proportions.filter(function (p) {
                    return p.value > 0;
                });
                if (!hasMeta && activeGroups.length > 0) {
                    html += '<tr><td style="color:#666; padding:3px 0; vertical-align:top; white-space:nowrap;">Groups:</td><td style="padding:3px 4px;">';
                    activeGroups.forEach(function (p) {
                        html += '<div style="margin:2px 0; display:flex; align-items:center;">' +
                            '<span style="display:inline-block; width:12px; height:12px; background:' + p.color + '; border:1px solid #ccc; border-radius:2px; margin-right:5px; flex-shrink:0;"></span>' +
                            '<span>' + p.group + ': <b>' + p.value + '</b></span></div>';
                    });
                    html += '</td></tr>';
                }

                if (hasMeta && node.metaRings && node.metaRings.length > 0) {
                    html += '<tr><td style="color:#666; padding:3px 0; vertical-align:top; white-space:nowrap;">Metadata:</td><td style="padding:3px 4px;">';
                    node.metaRings.forEach(function (ring) {
                        html += '<div style="margin:2px 0 6px 0;">' +
                            '<div style="font-weight:bold; font-size:11px;">' +
                            (ring.trait || 'Trait') + '</div>';
                        if (ring.kind === 'continuous') {
                            html += '<div style="display:flex; align-items:center;">' +
                                '<span style="display:inline-block; width:12px; height:12px; background:' +
                                (ring.color || '#fff') +
                                '; border:1px solid #ccc; border-radius:2px; margin-right:5px;"></span>' +
                                '<span>Mean: ' + (ring.value === null || ring.value === undefined
                                    ? '(missing)' : formatMetaLegendNumber(ring.value)) +
                                '</span></div>';
                            if ((ring.segments || []).length > 1) {
                                ring.segments.forEach(function (segment) {
                                    html += '<div style="display:flex; align-items:center; margin-left:8px;">' +
                                        '<span style="display:inline-block; width:10px; height:10px; background:' +
                                        (segment.color || '#fff') +
                                        '; border:1px solid #ccc; border-radius:2px; margin-right:5px;"></span>' +
                                        '<span>' + (segment.label === '' ? '(missing)' :
                                            formatMetaLegendNumber(segment.label)) +
                                        ': <b>' + segment.value + '</b></span></div>';
                                });
                            }
                        } else {
                            (ring.segments || []).forEach(function (segment) {
                                html += '<div style="display:flex; align-items:center;">' +
                                    '<span style="display:inline-block; width:12px; height:12px; background:' +
                                    (segment.color || '#ddd') +
                                    '; border:1px solid #ccc; border-radius:2px; margin-right:5px;"></span>' +
                                    '<span>' + (segment.label || '(missing)') + ': <b>' +
                                    segment.value + '</b></span></div>';
                            });
                        }
                        html += '</div>';
                    });
                    html += '</td></tr>';
                }
            }

            html += '</table>';

            if (names.length > 1) {
                html += '<div style="margin-top:10px;">';
                html += '<div style="color:#666; font-size:11px; margin-bottom:4px; font-weight:bold;">Sequences (' + names.length + '):</div>';
                nameEntries.forEach(function (entry) {
                    var s = entry.id;
                    var rec = null;
                    if (w2ui.haplotypes) {
                        var found = w2ui.haplotypes.find({recid: s}, true);
                        if (found && found.length > 0) rec = w2ui.haplotypes.records[found[0]];
                    }
                    var seqGroup = rec ? rec.group : null;
                    var seqTime = (rec && rec.time !== undefined && !isNaN(rec.time)) ? rec.time : null;
                    var seqColor = rec ? '#' + rec.color : null;

                    var tagHtml = '';
                    if (seqGroup && seqGroup !== 'Default') {
                        var textColor = (parseInt(rec.color, 16) > 8388607) ? '#000' : '#fff';
                        tagHtml += '<span style="display:inline-block; background:' + seqColor + '; color:' + textColor +
                            '; font-size:10px; padding:1px 5px; border-radius:3px; margin-left:4px; vertical-align:middle;">' +
                            seqGroup + '</span>';
                    }
                    if (seqTime !== null) {
                        tagHtml += '<span style="display:inline-block; background:#e0f0ff; color:#1a5276; font-size:10px; ' +
                            'padding:1px 5px; border-radius:3px; margin-left:4px; vertical-align:middle;">' +
                            seqTime + '</span>';
                    }

                    html += '<div style="font-size:11px; background:#f0f2f5; padding:3px 6px; margin:2px 0; border-radius:2px; ' +
                        'display:flex; align-items:center; justify-content:space-between;">' +
                        '<span style="word-break:break-all;">' + escapeHtml(entry.label) + '</span>' +
                        (tagHtml ? '<span style="white-space:nowrap; margin-left:4px;">' + tagHtml + '</span>' : '') +
                        '</div>';
                });
                html += '</div>';
            }

            if (isHaplotype) {
                var isHighlighted = highlightNode.indexOf(node.name) >= 0;
                var haplotypeVisible = isNodeTextVisible(node, 'haplotype');
                var nameIdVisible = isNodeTextVisible(node, 'nameId');
                var haplotypeLayout = getNodeTextLayout(node, 'haplotype');
                var nameIdLayout = getNodeTextLayout(node, 'nameId');
                html += '<div style="margin-top:12px; border-top:1px solid #eee; padding-top:10px;">';
                html += '<div style="color:#555; font-size:12px; font-weight:bold; margin-bottom:7px;">Node Text</div>';

                html += '<div style="background:#f7f8fa; border:1px solid #e4e7eb; border-radius:4px; padding:7px; margin-bottom:8px;">';
                html += '<button id="info-haplotype-label-btn" class="w2ui-btn" style="width:100%; margin-bottom:7px;">' +
                    (haplotypeVisible ? 'Hide Haplotype' : 'Show Haplotype') + '</button>';
                html += '<div style="font-size:10px; color:#777; margin-bottom:4px;">Position relative to node centre (px)</div>';
                html += '<div style="display:grid; grid-template-columns:18px 1fr 18px 1fr; gap:4px; align-items:center; font-size:10px;">' +
                    '<label for="info-hap-x">X</label><input id="info-hap-x" type="number" step="1" value="' + haplotypeLayout.x + '" style="width:100%; box-sizing:border-box;" />' +
                    '<label for="info-hap-y">Y</label><input id="info-hap-y" type="number" step="1" value="' + haplotypeLayout.y + '" style="width:100%; box-sizing:border-box;" />' +
                    '</div>';
                html += '<div style="display:grid; grid-template-columns:48px 1fr; gap:4px; align-items:center; font-size:10px; margin-top:4px;">' +
                    '<label for="info-hap-size">Size (px)</label><input id="info-hap-size" type="number" min="1" max="200" step="1" value="' + haplotypeLayout.size + '" style="width:100%; box-sizing:border-box;" />' +
                    '</div></div>';

                html += '<div style="background:#f7f8fa; border:1px solid #e4e7eb; border-radius:4px; padding:7px; margin-bottom:8px;">';
                if (nameEntries.length > 0) {
                    var selectedNameId = getNodeNameIdLabel(node);
                    html += '<label for="info-name-id-select" style="display:block; color:#666; font-size:11px; margin-bottom:4px;">Displayed Name/ID:</label>';
                    html += '<select id="info-name-id-select" style="width:100%; margin-bottom:7px;">';
                    nameEntries.forEach(function (entry, index) {
                        html += '<option value="' + index + '"' +
                            (entry.label === selectedNameId ? ' selected' : '') + '>' +
                            escapeHtml(entry.label) + '</option>';
                    });
                    html += '</select>';
                }
                html += '<button id="info-name-id-label-btn" class="w2ui-btn" style="width:100%; margin-bottom:7px;">' +
                    (nameIdVisible ? 'Hide Name/ID' : 'Show Name/ID') + '</button>';
                html += '<div style="font-size:10px; color:#777; margin-bottom:4px;">Position relative to node centre (px)</div>';
                html += '<div style="display:grid; grid-template-columns:18px 1fr 18px 1fr; gap:4px; align-items:center; font-size:10px;">' +
                    '<label for="info-name-x">X</label><input id="info-name-x" type="number" step="1" value="' + nameIdLayout.x + '" style="width:100%; box-sizing:border-box;" />' +
                    '<label for="info-name-y">Y</label><input id="info-name-y" type="number" step="1" value="' + nameIdLayout.y + '" style="width:100%; box-sizing:border-box;" />' +
                    '</div>';
                html += '<div style="display:grid; grid-template-columns:48px 1fr; gap:4px; align-items:center; font-size:10px; margin-top:4px;">' +
                    '<label for="info-name-size">Size (px)</label><input id="info-name-size" type="number" min="1" max="200" step="1" value="' + nameIdLayout.size + '" style="width:100%; box-sizing:border-box;" />' +
                    '</div></div>';

                html += '<div style="display:flex; gap:5px; margin-bottom:10px;">' +
                    '<button id="info-text-settings-btn" class="w2ui-btn" style="flex:1;">Apply Text</button>' +
                    '<button id="info-text-reset-btn" class="w2ui-btn" style="flex:1;">Reset Position</button>' +
                    '</div>';
                html += '<button id="info-highlight-btn" class="w2ui-btn" style="width:100%; margin-bottom:6px;">' +
                    (isHighlighted ? 'Remove Highlight' : 'Highlight Node') + '</button>';
                html += '</div>';
            }

            html += '</div>';
            $('#node-info-panel').html(html);

            if (isHaplotype) {
                $('#info-name-id-select').change(function () {
                    var selectedIndex = Number($(this).val());
                    if (nameEntries[selectedIndex]) {
                        nodeNameId[node.name] = nameEntries[selectedIndex].label;
                        if (isNodeTextVisible(node, 'nameId')) updateSVG();
                        showNodeInfo(node);
                    }
                });
                $('#info-haplotype-label-btn').click(function () {
                    labelNode[node.name] = !isNodeTextVisible(node, 'haplotype');
                    updateSVG();
                    showNodeInfo(node);
                });
                $('#info-name-id-label-btn').click(function () {
                    nameIdNode[node.name] = !isNodeTextVisible(node, 'nameId');
                    updateSVG();
                    showNodeInfo(node);
                });
                $('#info-text-settings-btn').click(function () {
                    var hapValues = {
                        x: Number($('#info-hap-x').val()),
                        y: Number($('#info-hap-y').val()),
                        size: Number($('#info-hap-size').val())
                    };
                    var nameValues = {
                        x: Number($('#info-name-x').val()),
                        y: Number($('#info-name-y').val()),
                        size: Number($('#info-name-size').val())
                    };
                    var values = [hapValues, nameValues];
                    var valid = values.every(function (item) {
                        return isFinite(item.x) && isFinite(item.y) &&
                            isFinite(item.size) && item.size >= 1 && item.size <= 200;
                    });
                    if (!valid) {
                        w2alert('Text X/Y must be numbers and Size must be between 1 and 200 px.');
                        return;
                    }
                    setNodeTextLayout(node, 'haplotype', hapValues);
                    setNodeTextLayout(node, 'nameId', nameValues);
                    updateSVG();
                    showNodeInfo(node);
                });
                $('#info-text-reset-btn').click(function () {
                    delete nodeTextLayout[nodeLabelKey(node)];
                    updateSVG();
                    showNodeInfo(node);
                });
                $('#info-highlight-btn').click(function () {
                    var idx = highlightNode.indexOf(node.name);
                    if (idx >= 0) highlightNode.splice(idx, 1);
                    else highlightNode.push(node.name);
                    updateSVG();
                    showNodeInfo(node);
                });
            }
        }

        /*
         * Show edge information in the right panel.
         */
        function showLinkInfo(link) {
            var srcLabel = getNodeDisplayLabel(link.source);
            var tgtLabel = getNodeDisplayLabel(link.target);
            var lid = link.id;

            var html = '<div style="padding:10px;">';
            html += '<div style="font-weight:bold; font-size:16px; color:#2d4a6a; border-bottom:2px solid #2d4a6a; padding-bottom:6px; margin-bottom:10px;">' +
                srcLabel + ' &#8594; ' + tgtLabel + '</div>';

            html += '<table style="width:100%; font-size:12px; border-collapse:collapse;">';
            html += '<tr><td style="color:#666; padding:3px 0; white-space:nowrap; width:70px;">From:</td>' +
                '<td style="padding:3px 4px;">' + srcLabel + '</td></tr>';
            html += '<tr><td style="color:#666; padding:3px 0; white-space:nowrap;">To:</td>' +
                '<td style="padding:3px 4px;">' + tgtLabel + '</td></tr>';
            if (link.changes) {
                html += '<tr><td style="color:#666; padding:3px 0; white-space:nowrap; vertical-align:top;">Changes:</td>' +
                    '<td style="padding:3px 4px; word-break:break-all;">' + link.changes + '</td></tr>';
            }
            html += '</table>';

            var isHighlighted = highlightLink.indexOf(lid) >= 0;
            var hasLabel = labelLink.hasOwnProperty(lid);
            html += '<div style="margin-top:12px; border-top:1px solid #eee; padding-top:10px;">';
            html += '<button id="info-link-highlight-btn" class="w2ui-btn" style="width:100%; margin-bottom:6px;">' +
                (isHighlighted ? 'Remove Highlight' : 'Highlight Edge') + '</button>';
            html += '<button id="info-link-label-btn" class="w2ui-btn" style="width:100%;">' +
                (hasLabel ? 'Hide Changes Count' : 'Show Changes Count') + '</button>';
            html += '</div>';
            html += '</div>';
            $('#node-info-panel').html(html);

            $('#info-link-highlight-btn').click(function () {
                var idx = highlightLink.indexOf(lid);
                if (idx >= 0) highlightLink.splice(idx, 1);
                else highlightLink.push(lid);
                updateSVG();
                showLinkInfo(link);
            });
            $('#info-link-label-btn').click(function () {
                if (labelLink.hasOwnProperty(lid)) {
                    delete labelLink[lid];
                } else {
                    var count = link.changes ? link.changes.toString() : '?';
                    labelLink[lid] = count;
                }
                updateSVG();
                showLinkInfo(link);
            });
        }

        /*
         * Delete a selected link
         */

        clickLink = function (e) {
            if (deletelink) {
                pushUndoSnapshot();
                linkList.splice(linkList.indexOf(e), 1);
                var srcId = e.source.id, tgtId = e.target.id;
                edgeList = edgeList.filter(function (edge) {
                    return !((edge.source === srcId && edge.target === tgtId) ||
                        (edge.source === tgtId && edge.target === srcId));
                });
                updateSVG();
            } else {
                activeInfoNode = null;
                showLinkInfo(e);
            }
        };

        /*
        function massChanged(path, e){
          var arcOver = d3.svg.arc().outerRadius(function(d) { return d.data.radius*e; });
          path.transition().duration(1000).attr("d", arcOver);
         // force.start();
        };
        $('#massFactor').on('change', function (event){ event.onComplete = massChanged(path, event.target.value) } );
        */

        /*
         * charge changed during operation
         */

        function chargeChanged(e) {
            force.stop();
            chrg = e;
            force.start();
        }

        $('#charge').on('change', function (event) {
            event.onComplete = chargeChanged(event.target.value);
        });

        /*
         * linkDistance changed
         */

        function linkDistanceChanged(e) {
            force.stop();
            lnkdist = e;
            force.start();
        }

        $('#linkDistance').on('change', function (event) {
            event.onComplete = linkDistanceChanged(event.target.value);
        });

        /*
         *  linkStrength changed
         */

        function linkStrengthChanged(e) {
            lnkstre = Number(e);
            force.stop().linkStrength(lnkstre).start();
        }

        $('#linkStrength').on('change', function (event) {
            event.onComplete = linkStrengthChanged(event.target.value);
        });

        /*
         * friction changed
         */

        function frictionChanged(e) {
            frict = Number(e);
            force.stop().friction(frict).start();
        }

        $('#friction').on('change', function (event) {
            event.onComplete = frictionChanged(event.target.value);
        });

        /*
         * chargeDistance changed
         *
         * Better not to mess with this
         */

        /*
        function chargeDistanceChanged(e){
          //console.log('Dist:',e)
          //if(e==='') e =100000;
          force.stop().chargeDistance(e).start();
          //if(e>10000) e = Infinity;
          //force.start();
        };
        $('#chargeDistance').on('change', function (event){ event.onComplete = chargeDistanceChanged(event.target.value) } );
        */

        /*
         * gravity changed
         */

        function gravityChanged(e) {
            grav = Number(e);
            force.stop().gravity(grav).start();
        }

        $('#gravity').on('change', function (event) {
            event.onComplete = gravityChanged(event.target.value);
        });

        /*
         * Update current/default values in UI controls.
         */

        $('#linkDistance').attr('value', lnkdist);
        $('#linkStrength').attr('value', lnkstre);
        $('#friction').attr('value', frict);
        $('#charge').attr('value', chrg);
        // Do not mess with this
        //$('#chargeDistance').attr('value', chrgdist);
        $('#gravity').attr('value', grav);
        $('#typeid').attr('value', typeid);
        $('#advNodeRadius').attr('value', standardRadius);
        $('#advNodeLineWidth').attr('value', nodeLineWidth);
        $('#advEdgeLineWidth').attr('value', edgeLineWidth);
        $('#advEdgeWeightScale').attr('value', edgeWeightScale);
        $('#advMetaRingLineWidth').attr('value', metaRingLineWidth);
        $('#advTextOffset').attr('value', textOffset);
        $('#advHaplotypeFontSize').attr('value', haplotypeFontSize);
        $('#advNameIdFontSize').attr('value', nameIdFontSize);
        $('#advMetaRingRatio').attr('value', metaRingRatio);
        $('#advMetaRingScales').attr('value', metaRingScales.join(', '));

        /*
         * Disable 'start' button
         */

        $('#start').prop('disabled', true).on('click', function (event) {
            /*
             * Disable 'start' button
             */
            $('#start').prop('disabled', true);
            /*
             * Enable stop button
             */
            $('#stop').prop('disabled', false);
            updateSVG();
        });

        $('#stop').prop('disabled', false).on('click', function (event) {
            /*
             * Disable 'stop' button
             */
            $('#stop').prop('disabled', true);
            /*
             * Enable 'start' button
             */
            $('#start').prop('disabled', false);
            force.stop();
        });

        $('#reset').prop('disabled', false);

        /*
         * Enable editing buttons
         */

        w2ui.Layout_main_toolbar.enable('btn-dellink', 'btn-delnode', 'btn-saveimage', 'btn-zoomin', 'btn-zoomout', 'btn-legend', 'btn-name-id', 'btn-distance', 'btn-edgeweight', 'btn-advanced');
        // btn-haplotype is only enabled after a 3-column hapconf file is loaded
        w2ui.Layout_main_toolbar.disable('btn-haplotype');


        /*
         * Now start the force layout algorithm and update the SVG.
         */

        updateSVG();

    }

    /*
     * Check for File API support. If enabled, go on...
     */

    if (window.File && window.FileReader && window.FileList && window.Blob) {

        /*
         * Check if FileSave.js works
         */

        try {
            var isFileSaverSupported = !!new Blob();
            filesave = true;
        } catch (e) {
            w2alert('FileSaver.js is not supported! Use a modern browser...<br>' + 'FileSaver.js is supported by Firefox 20+, Chrome, Chrome<br>' + 'for Android, IE 10+, Opera 15+ and Safari 6.1+', 'File Save Failed!');
        }

        /*
         * Define a general style for the GUI (w2ui)
         */

        const style = 'background-color: #F5F6F7; border: 1px solid silver; padding: 3px';

        const groups = getGroupsGrid(style);
        const haplotypes = getHaplotypesGrid(style);

        /*
         * Create a new layout
         */

        const layout = getLayout(style, groups, haplotypes);

        layout.html('top',
            '<div style="float: left;">' +
            '<button id="toggleLeft" class="w2ui-btn netst-toggle-btn" title="Show/hide the Data panel">' +
            '<span class="netst-toggle-icon">&#171;</span> Data</button>' +
            '<button id="loadData" class="w2ui-btn">Load Data</button>' +
            '</div>' +
            '<div style="float: right;">' +
            '<button id="help" class="w2ui-btn">Help</button>' +
            '<button id="toggleRight" class="w2ui-btn netst-toggle-btn" title="Show/hide the Haplotype Network Info panel">' +
            'Info <span class="netst-toggle-icon">&#187;</span></button>' +
            '</div>');
        // layout.html('top', '');
        layout.html('left', w2ui.haplotypes);
        layout.html('right',
            '<div style="display:flex; flex-direction:column; height:100%; box-sizing:border-box;">' +
            '<div style="padding:8px 10px; border-bottom:1px solid #e0e0e0; display:flex; gap:4px;">' +
            '<input id="node-search-input" type="text" placeholder="Search node..." ' +
            'style="flex:1; padding:5px 8px; border:1px solid #cfd8dd; border-radius:5px; font-size:12px; outline:none;" />' +
            '<button id="node-search-btn" class="w2ui-btn" style="padding:4px 10px; font-size:12px;">Go</button>' +
            '</div>' +
            '<div id="node-info-panel" style="padding:12px; overflow:auto; flex:1; box-sizing:border-box;">' +
            '<div style="color:#aaa; text-align:center; margin-top:60px; font-size:12px; line-height:1.6;">' +
            'Click a node or edge to<br>view its information' +
            '</div>' +
            '</div>' +
            '</div>');
        layout.html('main', '<div id="gview" style="width=100%; height=100%;">' + '<div style="width=50%; padding: 20%; font-size: 160%;">' + 'A paper describing tcsBU has been published in the journal <i>Bioinformatics</i>. ' + 'Please cite as: <p>Santos, AM, Cabezas MP, Tavares AI, Xavier R, ' + 'Branco M (2016) tcsBU: a tool to extend TCS network layout and ' + 'visualization. <i>Bioinformatics</i>, btv636 ' + '(<a href="https://academic.oup.com/bioinformatics/article/32/4/627/1744448/" ' + 'target="blank">doi: 10.1093/bioinformatics/btv636</a>)' + '</div>' + '</div>');
        layout.html('bottom', '');

        /*
         * Add a hidden <input> field to load a graph file (GML)
         */

        $('body').append('<input id="loadGraph" type="file" />');

        /*
         * Advanced Settings overlay popup
         */
        $('body').append(
            '<div id="advanced-settings-overlay" class="adv-overlay" style="display:none;">' +
            '<div class="adv-header" id="adv-header">' +
            '<span class="adv-title">Advanced Layout Setting</span>' +
            '<button id="close-advanced-settings" class="adv-close" title="Close">&#x00D7;</button>' +
            '</div>' +
            '<div class="adv-body">' +
            '<div class="adv-section">Force-Directed Layout Settings</div>' +
            '<div class="w2ui-field"><label>Link Distance:</label><div><input type="text" id="linkDistance" /></div></div>' +
            '<div class="w2ui-field"><label>Link Strength:</label><div><input type="text" id="linkStrength" /></div></div>' +
            '<div class="w2ui-field"><label>Friction:</label><div><input type="text" id="friction" /></div></div>' +
            '<div class="w2ui-field"><label>Charge:</label><div><input type="text" id="charge" /></div></div>' +
            '<div class="w2ui-field"><label>Gravity:</label><div><input type="text" id="gravity" /></div></div>' +
            '<div class="adv-btn-row">' +
            '<button class="w2ui-btn" id="start" name="start" disabled>Start</button>' +
            '<button class="w2ui-btn" id="stop" name="stop" disabled>Stop</button>' +
            '</div>' +
            '<div class="adv-section">Node and Edge Settings</div>' +
            '<div class="w2ui-field"><label>Node Radius:</label><div><input type="text" id="advNodeRadius" /></div></div>' +
            '<div class="adv-hint">Radius in pixels for a frequency-1 node. Relative node sizes are preserved.</div>' +
            '<div class="w2ui-field"><label>Node Line Width:</label><div><input type="text" id="advNodeLineWidth" /></div></div>' +
            '<div class="w2ui-field"><label>Edge Line Width:</label><div><input type="text" id="advEdgeLineWidth" /></div></div>' +
            '<div class="adv-hint">Base stroke width in pixels for edges between nodes.</div>' +
            '<div class="w2ui-field"><label>Edge Weight Scale:</label><div><input type="text" id="advEdgeWeightScale" /></div></div>' +
            '<div class="adv-hint">Maximum multiplier of Edge Line Width when Edge Weight is on. Edges thin toward the base width as Changes increases.</div>' +
            '<div class="w2ui-field"><label>Text Offset:</label><div><input type="text" id="advTextOffset" /></div></div>' +
            '<div class="w2ui-field"><label>Haplotype Font Size:</label><div><input type="text" id="advHaplotypeFontSize" /></div></div>' +
            '<div class="w2ui-field"><label>Name/ID Font Size:</label><div><input type="text" id="advNameIdFontSize" /></div></div>' +
            '<div class="adv-hint">Global font sizes in pixels. Applying these values updates every node label; individual nodes can still be adjusted in Info.</div>' +
            '<div class="adv-section">Metadata Ring Settings</div>' +
            '<div class="w2ui-field"><label>Ring Line Width:</label><div><input type="text" id="advMetaRingLineWidth" /></div></div>' +
            '<div class="w2ui-field"><label>Ring Width Ratio:</label><div><input type="text" id="advMetaRingRatio" /></div></div>' +
            '<div class="adv-hint">Ring width as a fraction of node radius. Each ring width = node radius \u00D7 ratio \u00D7 scale.</div>' +
            '<div class="w2ui-field"><label>Outer Ring Ratios:</label><div><input type="text" id="advMetaRingScales" placeholder="1, 1, 1" /></div></div>' +
            '<div class="adv-hint">Comma-separated ratios from inner to outer. Missing values use 1.</div>' +
            '<div id="advMetaRingOrder" class="adv-order"></div>' +
            '<div id="adv-layout-error" class="adv-error"></div>' +
            '<div class="adv-footer">' +
            '<button class="w2ui-btn" id="adv-cancel">Cancel</button>' +
            '<button class="w2ui-btn adv-primary" id="adv-apply">Apply</button>' +
            '</div>' +
            '</div>' +
            '</div>'
        );
        $('#close-advanced-settings').click(function () {
            $('#advanced-settings-overlay').hide();
        });
        // Make the dialog draggable by its header. On the first drag we switch
        // from the centering transform to explicit pixel coordinates so the
        // pointer stays locked to the grab point.
        (function () {
            var overlay = document.getElementById('advanced-settings-overlay');
            var header = document.getElementById('adv-header');
            if (!overlay || !header) return;
            var dragging = false, startX = 0, startY = 0, baseLeft = 0, baseTop = 0;
            header.addEventListener('mousedown', function (event) {
                if (event.target.id === 'close-advanced-settings') return;
                var rect = overlay.getBoundingClientRect();
                overlay.style.transform = 'none';
                overlay.style.left = rect.left + 'px';
                overlay.style.top = rect.top + 'px';
                baseLeft = rect.left;
                baseTop = rect.top;
                startX = event.clientX;
                startY = event.clientY;
                dragging = true;
                event.preventDefault();
            });
            document.addEventListener('mousemove', function (event) {
                if (!dragging) return;
                var left = baseLeft + (event.clientX - startX);
                var top = baseTop + (event.clientY - startY);
                // Keep the header on screen so the dialog can always be grabbed.
                var maxLeft = window.innerWidth - 60;
                var maxTop = window.innerHeight - 30;
                overlay.style.left = Math.min(maxLeft, Math.max(60 - overlay.offsetWidth, left)) + 'px';
                overlay.style.top = Math.min(maxTop, Math.max(0, top)) + 'px';
            });
            document.addEventListener('mouseup', function () {
                dragging = false;
            });
        })();


        $('#loadGraph').on('change', function (event) {
            loadGraph(event);
        });
        $('#loadData').click(function () {
            $('#loadGraph').click();
        });
        $('#node-search-btn').click(function () {
            searchNode($('#node-search-input').val());
        });
        $('#node-search-input').on('keydown', function (e) {
            if (e.which === 13) searchNode($(this).val());
        });
        $(document).on('keydown', function (e) {
            if ((e.ctrlKey || e.metaKey) && e.which === 90) {
                e.preventDefault();
                undoDelete();
            }
        });

        /*
         * Collapsible side panels. The Data (left) and Haplotype Network Info
         * (right) panels can be hidden to give the network more room; the top
         * bar buttons stay visible so a collapsed panel can always be reopened.
         * The chevron points outward when the panel is open (click to collapse)
         * and inward when it is hidden (click to reveal).
         */
        function netstUpdatePanelToggles() {
            if (!w2ui.Layout) return;
            var leftPanel = w2ui.Layout.get('left');
            var rightPanel = w2ui.Layout.get('right');
            if (leftPanel) {
                $('#toggleLeft .netst-toggle-icon').html(leftPanel.hidden ? '&#187;' : '&#171;');
            }
            if (rightPanel) {
                $('#toggleRight .netst-toggle-icon').html(rightPanel.hidden ? '&#171;' : '&#187;');
            }
        }

        $('#toggleLeft').click(function () {
            w2ui.Layout.toggle('left');
            netstUpdatePanelToggles();
        });
        $('#toggleRight').click(function () {
            w2ui.Layout.toggle('right');
            netstUpdatePanelToggles();
        });
        // Constrain both side-panel dividers to between 1/8 and 1/3 of the page
        // width. w2ui reads panel.minSize/maxSize live while dragging, so the
        // bounds are recomputed on window resize to stay proportional, and any
        // panel a shrinking window pushed past the new maximum is clamped back.
        function netstApplyPanelSizeBounds() {
            if (!w2ui.Layout) return;
            var pageWidth = window.innerWidth || document.documentElement.clientWidth || 1280;
            var minSize = Math.round(pageWidth / 8);
            var maxSize = Math.round(pageWidth / 3);
            var needResize = false;
            ['left', 'right'].forEach(function (type) {
                var panel = w2ui.Layout.get(type);
                if (!panel) return;
                panel.minSize = minSize;
                panel.maxSize = maxSize;
                var size = parseInt(panel.size, 10);
                if (!isNaN(size)) {
                    var clamped = Math.min(maxSize, Math.max(minSize, size));
                    if (clamped !== size) {
                        panel.size = clamped;
                        needResize = true;
                    }
                }
            });
            if (needResize && typeof w2ui.Layout.resize === 'function') {
                w2ui.Layout.resize();
            }
        }

        $(window).on('resize', netstApplyPanelSizeBounds);
        netstApplyPanelSizeBounds();
        netstUpdatePanelToggles();

        //$('#massFactor').w2field('float', { min: 1, max: 10, step: 0.5, arrows: true });
        $('#linkDistance').w2field('float', {min: 0.1, max: 10, step: 0.1, arrows: false});
        $('#linkStrength').w2field('float', {min: 0, max: 1, step: 0.02, arrows: false});
        $('#friction').w2field('float', {min: 0, max: 1, step: 0.02, arrows: false});
        $('#charge').w2field('int', {min: -1000, max: 1000, step: 10, arrows: false});
        // Do not mess with this!
        // $('#chargeDistance').w2field('int', { min: 0, step: 10, arrows: false });
        $('#gravity').w2field('float', {min: 0, max: 1, step: 0.001, arrows: false});
        $('#advNodeRadius').w2field('float', {min: 0.1, max: 100, step: 0.5, arrows: false});
        $('#advNodeLineWidth').w2field('float', {min: 0, max: 10, step: 0.1, arrows: false});
        $('#advEdgeLineWidth').w2field('float', {min: 0, max: 10, step: 0.1, arrows: false});
        $('#advEdgeWeightScale').w2field('float', {min: 1, max: 30, step: 0.5, arrows: false});
        $('#advMetaRingLineWidth').w2field('float', {min: 0, max: 10, step: 0.1, arrows: false});
        $('#advTextOffset').w2field('float', {min: 0, max: 50, step: 0.5, arrows: false});
        $('#advHaplotypeFontSize').w2field('float', {min: 1, max: 200, step: 1, arrows: false});
        $('#advNameIdFontSize').w2field('float', {min: 1, max: 200, step: 1, arrows: false});
        $('#advMetaRingRatio').w2field('float', {min: 0.05, max: 5, step: 0.05, arrows: false});

        $('#adv-apply').on('click', function () {
            var newNodeRadius = parseFloat($('#advNodeRadius').val());
            var newNodeLineWidth = parseFloat($('#advNodeLineWidth').val());
            var newEdgeLineWidth = parseFloat($('#advEdgeLineWidth').val());
            var newEdgeWeightScale = parseFloat($('#advEdgeWeightScale').val());
            var newMetaRingLineWidth = parseFloat($('#advMetaRingLineWidth').val());
            var newTextOffset = parseFloat($('#advTextOffset').val());
            var newHaplotypeFontSize = parseFloat($('#advHaplotypeFontSize').val());
            var newNameIdFontSize = parseFloat($('#advNameIdFontSize').val());
            var newMetaRingRatio = parseFloat($('#advMetaRingRatio').val());
            var ringScaleText = $.trim($('#advMetaRingScales').val());
            var newMetaRingScales = [];
            if (ringScaleText !== '') {
                newMetaRingScales = ringScaleText.split(',').map(function (value) {
                    return Number($.trim(value));
                });
            }

            var errors = [];
            if (isNaN(newNodeRadius) || newNodeRadius <= 0) {
                errors.push('Node Radius must be > 0.');
            }
            if (isNaN(newNodeLineWidth) || newNodeLineWidth < 0) {
                errors.push('Node Line Width must be \u2265 0.');
            }
            if (isNaN(newEdgeLineWidth) || newEdgeLineWidth < 0) {
                errors.push('Edge Line Width must be \u2265 0.');
            }
            if (isNaN(newEdgeWeightScale) || newEdgeWeightScale < 1) {
                errors.push('Edge Weight Scale must be \u2265 1.');
            }
            if (isNaN(newMetaRingLineWidth) || newMetaRingLineWidth < 0) {
                errors.push('Ring Line Width must be \u2265 0.');
            }
            if (isNaN(newTextOffset) || newTextOffset < 0) errors.push('Text Offset must be \u2265 0.');
            if (isNaN(newHaplotypeFontSize) || newHaplotypeFontSize < 1 || newHaplotypeFontSize > 200) {
                errors.push('Haplotype Font Size must be between 1 and 200 px.');
            }
            if (isNaN(newNameIdFontSize) || newNameIdFontSize < 1 || newNameIdFontSize > 200) {
                errors.push('Name/ID Font Size must be between 1 and 200 px.');
            }
            if (isNaN(newMetaRingRatio) || newMetaRingRatio <= 0) {
                errors.push('Ring Width Ratio must be > 0.');
            }
            if (newMetaRingScales.some(function (value) {
                return !isFinite(value) || value <= 0 || value > 20;
            })) {
                errors.push('Outer Ring Ratios must be comma-separated numbers > 0 and \u2264 20.');
            }

            var $err = $('#adv-layout-error');
            if (errors.length > 0) {
                $err.text(errors.join(' ')).show();
                return;
            }
            $err.hide();

            if (!svg) return;

            // Preserve frequency-derived relative sizes while changing the
            // radius of a frequency-1 haplotype node. Transition nodes keep
            // their small ancestor radius.
            if (newNodeRadius !== standardRadius) {
                var nodeScale = newNodeRadius / standardRadius;
                standardRadius = newNodeRadius;
                nodeList.forEach(function (node) {
                    if (node.nodestyle !== 1) return;
                    node.radius *= nodeScale;
                    node.proportions.forEach(function (proportion) {
                        proportion.radius *= nodeScale;
                    });
                    node.timeProportions.forEach(function (proportion) {
                        if (proportion.radius) proportion.radius *= nodeScale;
                    });
                });
                linkList.forEach(function (item) {
                    item.ldist = item.source.radius + item.target.radius +
                        defaultLinkDistance + defaultDistance;
                });
            }
            nodeLineWidth = newNodeLineWidth;
            edgeLineWidth = newEdgeLineWidth;
            edgeWeightScale = newEdgeWeightScale;
            metaRingLineWidth = newMetaRingLineWidth;
            textOffset = newTextOffset;
            haplotypeFontSize = newHaplotypeFontSize;
            nameIdFontSize = newNameIdFontSize;
            applyGlobalNodeFontSize('haplotype', haplotypeFontSize);
            applyGlobalNodeFontSize('nameId', nameIdFontSize);
            metaRingRatio = newMetaRingRatio;
            metaRingScales = newMetaRingScales;

            updateSVG();
            if (activeInfoNode && refreshActiveNodeInfo) refreshActiveNodeInfo(activeInfoNode);
            $('#advanced-settings-overlay').hide();
        });

        $('#adv-cancel').on('click', function () {
            // Restore inputs to current in-effect values and close
            $('#advNodeRadius').val(standardRadius);
            $('#advNodeLineWidth').val(nodeLineWidth);
            $('#advEdgeLineWidth').val(edgeLineWidth);
            $('#advEdgeWeightScale').val(edgeWeightScale);
            $('#advMetaRingLineWidth').val(metaRingLineWidth);
            $('#advTextOffset').val(textOffset);
            $('#advHaplotypeFontSize').val(haplotypeFontSize);
            $('#advNameIdFontSize').val(nameIdFontSize);
            $('#advMetaRingRatio').val(metaRingRatio);
            $('#advMetaRingScales').val(metaRingScales.join(', '));
            $('#adv-layout-error').hide();
            $('#advanced-settings-overlay').hide();
        });

        $('#help').click(function () {
            $().w2popup({
                url: 'help.html', title: 'tcsBU HELP', width: 800, height: 500,
            });
        });
    } else {
        w2alert('The File APIs are not fully supported by your browser.');
    }

    // Expose load functions globally so they can be called via QWebEngineView.runJavaScript
    // after the page has fully initialised (used when index.html is the persistent network view).
    window.loadGraph = loadGraph;
    window.loadGroups = loadGroups;
    window.loadHaplotypes = loadHaplotypes;
    window.loadTraits = loadTraits;
    window.loadMetaConfig = loadMetaConfig;
    window.exportProjectViewState = exportProjectViewState;
    window.applyProjectViewState = applyProjectViewState;
    window.exportMetaConfig = function () {
        if (!metaConfig) return null;
        // Return a detached JSON value so QWebEngine can safely serialize it
        // back to NetST's Metadata/Data tabs.
        return JSON.parse(JSON.stringify(metaConfig));
    };

    // Auto-load pre-embedded data files (set by generated {prefix}.js).
    // These globals are defined when the HTML was opened with a data script.
    if (typeof gmlfile !== 'undefined') {
        loadGraph(gmlfile);
        if (typeof groupconffile !== 'undefined') loadGroups(groupconffile);
        if (typeof hapconffile !== 'undefined') loadHaplotypes(hapconffile);
        if (typeof traitconffile !== 'undefined') loadTraits(traitconffile);
    }

});
