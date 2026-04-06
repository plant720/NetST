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
    var labelNode = {}, highlightNode = [], seqHapFlag = false, distanceFlag = false;
    var highlightLink = [], labelLink = {};

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

    var deletelink = false, deletenode = false, outlinenodes = false;

    /*
     * Define some default values for 'force-directed layout' algorithm
     */

    var defaultDistance = 12, defaultGravity = 0.05, defaultCharge = -30, defaultLinkDistance = 1,
        defaultLinkStrength = 1, defaultFriction = 0.95;

    /*
     * standard radius for true haplogroups with 'frequency' = 1
     */

    var standardRadius = 5;
    var ancestorRadius = 1;
    var outerRadiusCoeff = 1.4;
    var innerRadiusCoeff = 0.7;
    var textOffset = 5;


    /*
     * Variables for the forced layout algorithm elements
     */
    var minTime = Number.POSITIVE_INFINITY;
    var maxTime = Number.NEGATIVE_INFINITY;


    var link, node, path, subpath, linkText;

    var pie, subPie, sector, sectorOuter, sectorNull, sectorSmall;

    var drag;

    var clickLink, clickNode;

    /*
     * Default line width
     */

    var linewidth = 1;

    var typeid = 0;

    var styleid = 0;

    /*
     * Flag indicating whether trait data has been loaded.
     * Inner ring is only drawn after traits are added.
     */
    var hasTrait = false;
    /*
     * Default zoom
     */

    var zoom = null;

    /*
     * Legend 0 -off, 1 - on
     */

    var legend = 0;

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
        var newcolor = 'ffffff', newpattern = 'none';

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


                /*
                 * Find the target svg element (node). If it exists, apply changes
                 */

                if (svg) {
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
                    if (outlinenodes) {
                        path.style('stroke-width', linewidth).style('stroke', '#000000');
                    } else {
                        path.style('stroke-width', '0').style('stroke', 'none');
                    }

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
                    if (outlinenodes) {
                        subpath.style('stroke-width', linewidth).style('stroke', '#000000');
                    } else {
                        subpath.style('stroke-width', '0').style('stroke', 'none');
                    }
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
     * t=0 → low time (dark/saturated), t=1 → high time (light/pale).
     * mode: 0=gray, 1=red, 2=green, 3=blue
     */
    function tcGradient(tc, mode) {
        var v = parseInt(tc, 16);
        var t = (v - 8) / 239;
        var r, g, b;
        var h = function(n) { return ('0' + Math.round(n).toString(16)).slice(-2); };
        if (mode === 0) { r = g = b = v; }
        else if (mode === 1) { r = 155 + 100 * t; g = 28 + 137 * t; b = 28 + 137 * t; }   // crimson → coral
        else if (mode === 2) { r = 22  + 112 * t; g = 101 + 138 * t; b = 52  + 120 * t; }  // forest → mint
        else if (mode === 3) { r = 30  + 117 * t; g = 58  + 139 * t; b = 138 + 115 * t; }  // navy → sky
        return '#' + h(r) + h(g) + h(b);
    }

    function openAdvancedSettings() {
        var overlay = $('#advanced-settings-overlay');
        overlay.toggle();
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
            .on('click', clickLink)
            .append('title')
            .text(function (d) {
                return d.changes;
            });
        link.style('stroke-width', linewidth).style('stroke', '#000000');
        link.exit().remove();

        // Apply link highlight and per-link changes labels.
        highlightLink.forEach(function (lid) {
            svg.select('#' + lid).style({'stroke': '#FF0000', 'stroke-width': linewidth * 3});
        });
        Object.keys(labelLink).forEach(function (lid) {
            var ldata = linkList.find(function (l) { return l.id === lid; });
            if (!ldata) return;
            svg.select('#' + lid)
                .each(function () {
                    var el = d3.select(this.parentNode);
                    el.append('text')
                        .attr('class', 'link-label-info')
                        .attr('x', function () { return (ldata.source.x + ldata.target.x) / 2; })
                        .attr('y', function () { return (ldata.source.y + ldata.target.y) / 2; })
                        .attr('text-anchor', 'middle')
                        .attr('dy', '-4px')
                        .text(labelLink[lid])
                        .style('font-family', 'Times New Roman')
                        .style('stroke-width', '0.2px')
                        .style('font-size', '11px')
                        .style('fill', '#c00');
                });
        });

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
                if (d.nodestyle === 1) {
                    if (!hasTrait || styleid === 1 || styleid === 2) return d.radius; else return d.radius * outerRadiusCoeff;
                } else {
                    return d.radius;
                }
            })
            .append('title')
            .text(function (d) {
                return d.name;
            });

        node.style('stroke-width', function () {
            return linewidth * 2;
        }).style('stroke', '#000000').style('fill', '#000000');
        node.exit().remove();


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
        if (outlinenodes) {
            path.style('stroke-width', linewidth / 2).style('stroke', '#000000');
        } else {
            path.style('stroke-width', '0').style('stroke', 'none');
        }
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
        if (outlinenodes) {
            subpath.style('stroke-width', linewidth / 2).style('stroke', '#000000');
        } else {
            subpath.style('stroke-width', '0').style('stroke', 'none');
        }

        subpath.exit().remove();

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

        // Apply highlight and label decorations based on the highlightNode and labelNode globals.
        highlightNode.forEach(function (name) {
            // Build a CSS selector, escaping any newline characters in the node name.
            var selector = '#' + name.replaceAll("\n", "\\a ");
            d3.select(selector).select(".node-circle").style({'stroke': '#FF0000', 'stroke-width': linewidth * 4});
        });

        Object.entries(labelNode).forEach(([key, value]) => {
            // Build a CSS selector, escaping any newline characters in the node name.
            var selector = '#' + key.replaceAll("\n", "\\a ");
            d3.select(selector)
                .append('text')
                .attr('class', 'node-text')
                .attr('dx', function (d) {
                    if (d.nodestyle === 1) {
                        if (!hasTrait || styleid === 1 || styleid === 2) return textOffset + d.radius; else return textOffset + d.radius * outerRadiusCoeff;
                    } else {
                        return textOffset + d.radius;
                    }
                })
                .attr('dy', '.35em')
                .text(value.join(";"))
                .style('font-family', 'Times New Roman') // Set the font family
                .style("stroke-width", '0.2px')
                .style('font-size', '13px');
        });

        // If enabled, show the hap label (from 3-col hapconf) on every haplotype node in the SVG.
        if (seqHapFlag) {
            d3.selectAll('.node')
                .each(function (d) {
                    if (!d.hap) return;
                    d3.select(this)
                        .append('text')
                        .attr('class', 'node_hap')
                        .attr('dx', function (d) {
                            if (d.nodestyle === 1) {
                                if (!hasTrait || styleid === 1 || styleid === 2) {
                                    return textOffset + d.radius;
                                } else {
                                    return textOffset + d.radius * outerRadiusCoeff;
                                }
                            } else {
                                return textOffset + d.radius;
                            }
                        })
                        .attr('dy', '.50em')
                        .text(d.hap)
                        .style('font-family', 'Times New Roman')
                        .style("stroke-width", '0.2px')
                        .style('font-size', '13px');
                });
        }
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
            }], records: [{recid: 'Default', color: 'ffffff', pattern: 'none', editable: false}], toolbar: {
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

                            if (sel === 0) {
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
                switch (e.column) {
                    case 0:  // Change a name

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
                        }
                        break;
                    case 1: // Change a color

                        w2ui.groups.records[e.index].color = e.value_new;

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

                        v = w2ui.haplotypes.find({group: e.recid}, true);
                        if (typeof v !== 'undefined' && v.length > 0) {
                            for (i = 0; i < v.length; i++) {
                                w2ui.haplotypes.records[v[i]].color = e.value_new;
                                if (svg) classify(v[i], e.recid, e.recid);
                            }
                        }
                        break;

                    case 2: // Change a pattern

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

                            v = w2ui.haplotypes.find({group: e.recid}, true);
                            if (typeof v !== 'undefined' && v.length > 0) {
                                for (i = 0; i < v.length; i++) {
                                    classify(v[i], e.recid, e.recid);
                                }
                            }
                        }
                        break;
                }

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
                    w2ui.haplotypes.records[e.index].color = 'ffffff';
                }

                classify(e.index, e.value_new, e.value_original);
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

    /*
     * The traits (characters) grid.
     * Displays a list of sequence IDs and their continuous time trait values read
     * from a semicolon-delimited traitconf file (seqname;value, no header row).
     */
    function getTraitsGrid() {

        /*
         * Append a hidden <input> element at the end of the body. This will serve as an anchor
         * used by button 'loadTraits' to browse files for reading a traitconf file
         * (semicolon-delimited, first column = seqname, second column = continuous time value).
         */

        $('body').append('<input id="loadTraits" type="file" />');

        /*
         * After selecting a file, this triggers the loadTraits function.
         */

        $('#loadTraits').on('change', function (e) {
            loadTraits(e);
        });

        $().w2grid({
            name: 'characters', multiSelect: false, show: {
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
                field: 'recid', caption: 'ID', size: '55%', sortable: true, resizable: true
            }, {
                field: 'traitValue', caption: 'Value', size: '45%', sortable: true, resizable: true
            }], toolbar: {
                items: [{
                    type: 'button', id: 'load_characters', text: 'Load', icon: 'icon-folder-open'
                }, {
                    type: 'button', id: 'save_characters', text: 'Save', icon: 'icon-file-save'
                }], onClick: function (e) {
                    switch (e.target) {
                        case 'load_characters':
                            if (!hapconfLoaded) {
                                w2alert('Please load a haplotype configuration file first<br>before importing a trait configuration file.', 'No haplotype data!');
                            } else {
                                $('#loadTraits').click();
                            }
                            break;
                        case 'save_characters':
                            saveTraits();
                            break;
                    }
                }
            }
        });

        // Return the grid object if successfully created, otherwise null.
        if (w2ui.characters) return w2ui.characters; else return null;
    }


    function insertLegend() {
        if (legend === 0) {
            legend = 1;
            var svgEl = d3.select('svg');

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
                svgEl.append('g').attr('transform', 'translate(50,140)').attr('class', 'legend').call(verticalLegend);
            }

            // styleid 0 (Dual-Trait) or 2 (Continuous): show trait gradient bar
            if ((styleid === 0 || styleid === 2) && typeid !== 4 && hasTrait) {
                var minColor = tcGradient('08', typeid);
                var maxColor = tcGradient('f7', typeid);

                var gradBarW = 20, gradBarH = 120;
                // Same x column as group legend; if also showing groups, place below them
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

                var traitCoords = {x: gradX, y: gradY};
                var legendG = svgEl.append('g')
                    .data([traitCoords])
                    .attr('transform', 'translate(' + gradX + ',' + gradY + ')')
                    .attr('class', 'legend legend-trait')
                    .style('cursor', 'move');

                // Drag — same pattern as group legend
                var drag = d3.behavior.drag()
                    .on('drag', function(d) {
                        d.x += d3.event.dx;
                        d.y += d3.event.dy;
                        d3.select(this).attr('transform', 'translate(' + [d.x, d.y] + ')');
                    })
                    .on('dragstart', function() {
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
        }
    }

    /*
     * Construct the layout
     */

    function getLayout(style, groups, haplotypes, characters) {
        $('#layout').w2layout({
            name: 'Layout', padding: 0, panels: [
                {type: 'top', size: 40, resizable: false, style: style},
                {type: 'left', size: 350, maxSize: 350, resizable: true, title: 'Data', style: style, tabs: {
                    name: 'tabs',
                    active: 'tab1',
                    tabs: [{id: 'tab2', text: 'Groups'}, {id: 'tab1', text: 'Haplotypes'},{id: 'tab3', text: 'Traits'},],
                    onClick: function (id) {
                        switch (id.target) {
                            case 'tab1':
                                w2ui.Layout.content('left', haplotypes);
                                break;
                            case 'tab2':
                                w2ui.Layout.content('left', groups);
                                break;
                            case 'tab3':
                                w2ui.Layout.content('left', characters);
                                break;
                        }
                    }

                }
            }, {type: 'right', size: 280, resizable: false, title: 'Haplotype Network Info', style: style}, {
                type: 'main', size: '100%', overflow: 'hidden', style: style, toolbar: {
                    items: [{
                        id: 'btn-svgsave', type: 'button', text: 'Save SVG', icon: 'icon-file-svg', disabled: true
                    }, //{ id: 'btn-pdfsave', type: 'button', text: 'Save PDF', icon: 'icon-file-pdf-o', disabled: true },
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
                            id: 'btn-outline',
                            type: 'check',
                            text: 'Outline',
                            icon: 'icon-outline',
                            disabled: true,
                            checked: false
                        }, {
                            id: 'btn-time',
                            type: 'menu',
                            text: 'Circle Center',
                            icon: 'icon-circles-2',
                            disabled: true,
                            items: [{text: 'Gray', typeid: "0"}, {text: 'Red', typeid: "1"}, {
                                text: 'Green', typeid: "2"
                            }, {text: 'Blue', typeid: "3"}]
                        }, {
                            id: 'btn-style',
                            type: 'menu',
                            text: 'Style',
                            icon: 'icon-cross-4',
                            disabled: true,
                            items: [{text: 'Dual-Trait', styleid: "0"}, {text: 'Category', styleid: "1"}, {
                                text: 'Continuous', styleid: "2"
                            },]
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
                            id: 'btn-distance',
                            type: 'check',
                            text: 'Distance',
                            icon: 'icon-label',
                            disabled: true,
                            checked: false
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
                            case 'btn-svgsave':
                                saveSVG();
                                break;
                            case 'btn-outline':
                                outlinenodes = !e.item.checked;
                                if (svg) updateSVG();
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
                            case 'btn-distance':
                                insertDistance()
                                break;
                            case 'btn-advanced':
                                openAdvancedSettings();
                                break;
                            default:
                                if (target.indexOf('btn-time:') !== -1) {
                                    typeid = parseInt(e.subItem.typeid);
                                    if (svg) updateSVG();
                                }
                                if (target.indexOf('btn-style:') !== -1) {
                                    var requestedStyle = parseInt(e.subItem.styleid);
                                    if (!hasTrait && requestedStyle !== 1) {
                                        w2alert('Please load trait data first before selecting<br>Dual-Trait or Continuous style.', 'Trait data required!');
                                    } else {
                                        styleid = requestedStyle;
                                        if (svg) updateSVG();
                                    }
                                }
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

        reader.onload = function () {
            var text = reader.result;
            var lines = text.split('\n');
            var newnode = false;
            var newedge = false;
            var multilabels = false;
            var frequency, radius, haplogroup, label, changes, source, target;
            var labels = [];
            for (var i = 0; i < lines.length; i++) {
                if (lines[i].indexOf('node [') === 3) newnode = true;
                if (lines[i].indexOf('edge [') === 3) newedge = true;
                if (lines[i].indexOf(']') === 3) {
                    if (newnode) {
                        newnode = false;
                        if (labels.length > 0) {
                            radius = standardRadius;
                            if (label !== '') {

                                /* This is a true haplotype (not a transition node). Add it
                                 * to the haplotypes' list that will be presented in the grid
                                 * 'haplotypes'. Make sure labels start with a character (not
                                 * a digit) and have only [a-zA-Z0-9_-] characters. Replace all
                                 * other characters by '_'. The reason for this is that although
                                 * JQuery can handle most of these and other characters as
                                 * element's ids, d3.js is much more restrictive...
                                 */
                                var nodestyle = 1;

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
                                        color: 'ffffff',
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
                                    color: '#ffffff',
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
            styleid = 1;

            /*
             * Clear any haplotypes present in the haplotypes' grid
             */

            if (w2ui.haplotypes.records.length > 0) w2ui.haplotypes.clear();

            /*
             * Clear any groups defined except Default
             */

            if (w2ui.groups.records.length > 1) {
                w2ui.groups.clear();
                w2ui.groups.add({recid: 'Default', color: 'ffffff', pattern: 'none', editable: false});
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
            var names = [];
            var g = [{recid: 'Default', color: 'ffffff', pattern: 'none', editable: false}];
            for (i = 0; i < lines.length; i++) {
                line = lines[i].trim();
                if (line !== '') {
                    l = line.split(";");
                    if (l.length === 2 || l.length === 3) {   // Accept only lines with two or three fields
                        name = l[0].trim();
                        if (name !== '') {                       // There is at least a label or name or something as a first field...
                            k = names.indexOf(name);                // Check if this name is already in list
                            if (k === -1) {
                                names.push(name);                     // Add name to the names' list
                                color = l[1].trim();                    // read the color
                                if (/^#[0-9a-f]{3,6}$/i.test(color)) {  // check if it is a valid RGB color (e.g, #a2ff4b or #a0f)
                                    color = color.substr(1);              // strip the # prefix
                                }
                                pattern = 'none';
                                if (typeof l[2] !== 'undefined') {   // read an optional pattern
                                    p = l[2].trim();
                                    j = pattern_names.filter(function (v) {
                                        return v.id === p;
                                    })[0];
                                    if (typeof j !== 'undefined') pattern = p;
                                }
                                g.push({recid: name, color: color, pattern: pattern});
                            }
                        }
                    }
                }
            }
            if (g.length > 1) {

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
                        w2ui.haplotypes.records[i].color = 'ffffff';
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
     * Updates matching haplotype time values, rebuilds timeProportions in nodeList,
     * and populates the 'characters' grid with columns ID and Value.
     */
    function loadTraits(e) {

        var input = e.target;

        if (input.files.length !== 1) return;

        var fileInput = document.getElementById('loadTraits');

        var reader = new FileReader();

        reader.onload = function () {
            var text = reader.result;
            var lines = text.split('\n');
            var traitsInfo = [];

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
                traitsInfo.push({recid: seqname, traitValue: value});
            }

            // Compute minTime/maxTime by matching seqnames directly against nodeList names.
            // Each node's name field contains one or more sequence names joined by '\n'.
            minTime = Number.POSITIVE_INFINITY;
            maxTime = Number.NEGATIVE_INFINITY;
            nodeList.forEach(function (node) {
                if (node.nodestyle !== 1) return;
                var seqs = node.name.split('\n').filter(function (s) { return s.trim() !== ''; });
                seqs.forEach(function (seq) {
                    var t = traitMap[seq.trim()];
                    if (t !== undefined) {
                        minTime = Math.min(minTime, t);
                        maxTime = Math.max(maxTime, t);
                    }
                });
            });

            // Determine style and build color scale.
            // Also mirror time/timecolor onto haplotype records for characters grid display.
            var colorScale = null;
            if (minTime !== maxTime) {
                styleid = 0;
                colorScale = d3.scale.linear()
                    .domain([minTime, maxTime])
                    .range([8, 247]);
            } else {
                styleid = 1;
            }

            // Update haplotype records with time and timecolor values (used by characters grid).
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
                var seqs = node.name.split('\n').filter(function (s) { return s.trim() !== ''; });
                seqs.forEach(function (seq) {
                    var t = traitMap[seq.trim()];
                    if (t === undefined) return; // seqname not in traitconf
                    var existing = node.timeProportions.find(function (tp) { return tp.time === t; });
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
            });

            w2ui.characters.clear();
            w2ui.characters.add(traitsInfo);

            hasTrait = true;
            if (svg) updateSVG();
        };

        /*
         * Capture the file reference before clearing the input, so readAsText
         * still receives a valid Blob (clearing fileInput.value invalidates input.files).
         */
        var file = input.files[0];
        fileInput.value = "";
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
            var line, l, name, group, seq2hap;
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
                        name = l[0].trim();
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
                            if (group !== "") h.push({label: name, group: group, seq2hap: seq2hap});
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
                    nodeList.forEach(function (node) { node.hap = null; });
                }

                hapconfLoaded = true;

                /*
                 * Enable the Haplotype toolbar button only when hap names are available (3-col).
                 */
                if (hapconfColumns === 3) {
                    w2ui.Layout_main_toolbar.enable('btn-haplotype');
                } else {
                    w2ui.Layout_main_toolbar.disable('btn-haplotype');
                }

                updateSVG();
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
        updateSVG();
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

    function saveTraits() {
        if (filesave) {
            var list = [];
            if (w2ui.characters.records.length > 0) {
                for (var i = 0; i < w2ui.characters.records.length; i++) {
                    list.push(w2ui.characters.records[i].recid + ';' + w2ui.characters.records[i].traitValue + '\n');
                }
                var blob = new Blob(list, {type: "text/plain;charset=utf-8"}, {endings: "native"});
                saveAs(blob, "traits.csv");
            }
        } else {
            w2alert('FileSaver.js is not supported! Use a modern browser...<br>' + 'FileSaver.js is supported by Firefox 20+, Chrome, Chrome<br>' + 'for Android, IE 10+, Opera 15+ and Safari 6.1+', 'FileSave.js is unsupported!');
        }
    }

    function saveSVG() {
        if (filesave) {
            var d = $('#gview');
            var blob = new Blob([d.html()], {type: "text/plain;charset=utf-8"});
            saveAs(blob, "network.svg");
        }
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

    function svgStart() {

        var massFactor = 0; // reserved for future node-mass scaling; currently unused
        var lnkdist = defaultLinkDistance;
        var lnkstre = defaultLinkStrength;
        var frict = defaultFriction;
        var chrg = defaultCharge;
        // Do not mess with this
        // var chrgdist = Infinity;
        var grav = defaultGravity;

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

        force.on("tick", function () {
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

            if (distanceFlag) {
                linkText
                    .attr('x', function (d) {
                        return (d.source.x + d.target.x) / 2;
                    })
                    .attr('y', function (d) {
                        return (d.source.y + d.target.y) / 2;
                    });
            }

            Object.keys(labelLink).forEach(function (lid) {
                var ldata = linkList.find(function (l) { return l.id === lid; });
                if (!ldata) return;
                var linkEl = svg.select('#' + lid);
                if (!linkEl.empty()) {
                    d3.select(linkEl.node().parentNode).select('.link-label-info')
                        .attr('x', (ldata.source.x + ldata.target.x) / 2)
                        .attr('y', (ldata.source.y + ldata.target.y) / 2);
                }
            });

            node.attr("x", function (d) {
                return d.x;
            })
                .attr("y", function (d) {
                    return d.y;
                })
                .attr("transform", function (d) {
                    return "translate(" + d.x + "," + d.y + ")";
                });
        });

        /*
         * Define costum drag
         */

        drag = force.drag().on("dragstart", function (d) {
            d3.event.sourceEvent.stopPropagation();
        });
        force.stop();
        /*
         * Delete a selected node
         */

        clickNode = function (e) {
            if (deletenode) {
                nodeList.splice(nodeList.indexOf(e), 1);
                var toSplice = linkList.filter(function (l) {
                    return (l.source === e) || (l.target === e);
                });
                toSplice.forEach(function (l) {
                    linkList.splice(linkList.indexOf(l), 1);
                });
                updateSVG();
            } else {
                showNodeInfo(e);
            }
        };

        /*
         * Show node information in the Node Info right panel.
         */
        function getHaplotypeLabel(node) {
            var haploNodes = nodeList.filter(function (n) { return n.nodestyle === 1; });
            var idx = haploNodes.indexOf(node);
            return idx >= 0 ? 'H' + (idx + 1) : null;
        }

        function getNodeDisplayLabel(node) {
            if (node.nodestyle !== 1) return 'Transition';
            // 3-col hapconf: use the hap name stored in node.hap (e.g. "H1")
            if (hapconfColumns === 3 && node.hap) return node.hap;
            // 2-col hapconf or no hapconf: use the first sequence name in the node
            var names = node.name ? node.name.split('\n').filter(function (s) { return s.trim() !== ''; }) : [];
            return names.length > 0 ? names[0] : getHaplotypeLabel(node);
        }

        function showNodeInfo(node) {
            var isHaplotype = node.nodestyle === 1;
            var haploLabel = getNodeDisplayLabel(node);
            var names = node.name ? node.name.split('\n').filter(function (s) { return s.trim() !== ''; }) : [];

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
                node.proportions.forEach(function (p) { freq += p.value; });
                html += '<tr><td style="color:#666; padding:3px 0; white-space:nowrap;">Frequency:</td>' +
                    '<td style="padding:3px 4px;">' + freq + '</td></tr>';

                var activeGroups = node.proportions.filter(function (p) { return p.value > 0; });
                if (activeGroups.length > 0) {
                    html += '<tr><td style="color:#666; padding:3px 0; vertical-align:top; white-space:nowrap;">Groups:</td><td style="padding:3px 4px;">';
                    activeGroups.forEach(function (p) {
                        html += '<div style="margin:2px 0; display:flex; align-items:center;">' +
                            '<span style="display:inline-block; width:12px; height:12px; background:' + p.color + '; border:1px solid #ccc; border-radius:2px; margin-right:5px; flex-shrink:0;"></span>' +
                            '<span>' + p.group + ': <b>' + p.value + '</b></span></div>';
                    });
                    html += '</td></tr>';
                }
            }

            html += '</table>';

            if (names.length > 1) {
                html += '<div style="margin-top:10px;">';
                html += '<div style="color:#666; font-size:11px; margin-bottom:4px; font-weight:bold;">Sequences (' + names.length + '):</div>';
                names.forEach(function (s) {
                    var rec = null;
                    if (w2ui.haplotypes) {
                        var found = w2ui.haplotypes.find({recid: s}, true);
                        if (found && found.length > 0) rec = w2ui.haplotypes.records[found[0]];
                    }
                    var seqGroup = rec ? rec.group : null;
                    var seqTime  = (rec && rec.time !== undefined && !isNaN(rec.time)) ? rec.time : null;
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
                        '<span style="word-break:break-all;">' + s + '</span>' +
                        (tagHtml ? '<span style="white-space:nowrap; margin-left:4px;">' + tagHtml + '</span>' : '') +
                        '</div>';
                });
                html += '</div>';
            }

            if (isHaplotype) {
                var isHighlighted = highlightNode.indexOf(node.name) >= 0;
                var hasLabel = labelNode.hasOwnProperty(node.name);
                html += '<div style="margin-top:12px; border-top:1px solid #eee; padding-top:10px;">';
                html += '<button id="info-highlight-btn" class="w2ui-btn" style="width:100%; margin-bottom:6px;">' +
                    (isHighlighted ? 'Remove Highlight' : 'Highlight Node') + '</button>';
                html += '<button id="info-label-btn" class="w2ui-btn" style="width:100%;">' +
                    (hasLabel ? 'Hide Haplotype Text' : 'Show Haplotype Text') + '</button>';
                html += '</div>';
            }

            html += '</div>';
            $('#node-info-panel').html(html);

            if (isHaplotype) {
                $('#info-highlight-btn').click(function () {
                    var idx = highlightNode.indexOf(node.name);
                    if (idx >= 0) highlightNode.splice(idx, 1);
                    else highlightNode.push(node.name);
                    updateSVG();
                    showNodeInfo(node);
                });
                $('#info-label-btn').click(function () {
                    if (labelNode.hasOwnProperty(node.name)) {
                        delete labelNode[node.name];
                    } else {
                        labelNode[node.name] = [haploLabel];
                    }
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
                linkList.splice(linkList.indexOf(e), 1);
                updateSVG();
            } else {
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
            force.stop().linkStrength(e).start();
        }

        $('#linkStrength').on('change', function (event) {
            event.onComplete = linkStrengthChanged(event.target.value);
        });

        /*
         * friction changed
         */

        function frictionChanged(e) {
            force.stop().friction(e).start();
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
            force.stop().gravity(e).start();
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
        $('#lwidth').attr('value', linewidth);
        $('#typeid').attr('value', typeid);
        $('#advStandRadius').attr('value', standardRadius);
        $('#advLineWidth').attr('value', linewidth);
        $('#advOuterRadiusCoeff').attr('value', outerRadiusCoeff);
        $('#advInnerRadiusCoeff').attr('value', innerRadiusCoeff);
        $('#advTextOffset').attr('value', textOffset);

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

        w2ui.Layout_main_toolbar.enable('btn-dellink', 'btn-delnode', 'btn-svgsave', 'btn-outline', 'btn-zoomin', 'btn-zoomout', 'btn-legend', 'btn-time', 'btn-style', 'btn-distance', 'btn-advanced');
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

        const characters = getTraitsGrid(style);

        /*
         * Create a new layout
         */

        const layout = getLayout(style, groups, haplotypes, characters);

        layout.html('top', '<div style="float: left;"><button id="loadData" class="w2ui-btn">Load Data</button></div><div style="float: right;"><button id="help" class="w2ui-btn">Help</button></div>');
        // layout.html('top', '');
        layout.html('left', w2ui.haplotypes);
        layout.html('right',
            '<div style="display:flex; flex-direction:column; height:100%; box-sizing:border-box;">' +
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
            '<div id="advanced-settings-overlay" style="display:none; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%);' +
            'background:#fff; border:1px solid #ccc; border-radius:4px; box-shadow:0 4px 20px rgba(0,0,0,0.35); z-index:9999; width:340px;">' +
            '<div style="background:#2d4a6a; color:#fff; padding:8px 14px; border-radius:4px 4px 0 0; display:flex; justify-content:space-between; align-items:center;">' +
            '<span style="font-weight:bold; font-size:13px;">Advanced Layout Setting</span>' +
            '<button id="close-advanced-settings" style="background:none; border:none; color:#fff; cursor:pointer; font-size:18px; line-height:1; padding:0;">&#x00D7;</button>' +
            '</div>' +
            '<div style="padding:15px 18px;">' +
            '<div style="font-weight:bold; font-size:12px; color:#2d4a6a; border-bottom:1px solid #ccc; padding-bottom:4px; margin-bottom:10px;">Force-Directed Layout Settings</div>' +
            '<div class="w2ui-field"><label>Link Distance:</label><div><input type="text" id="linkDistance" /></div></div>' +
            '<div class="w2ui-field"><label>Link Strength:</label><div><input type="text" id="linkStrength" /></div></div>' +
            '<div class="w2ui-field"><label>Friction:</label><div><input type="text" id="friction" /></div></div>' +
            '<div class="w2ui-field"><label>Charge:</label><div><input type="text" id="charge" /></div></div>' +
            '<div class="w2ui-field"><label>Gravity:</label><div><input type="text" id="gravity" /></div></div>' +
            '<p><div style="text-align:center;"><button class="w2ui-btn" id="start" name="start" disabled>Start</button></div></p>' +
            '<div style="text-align:center;"><button class="w2ui-btn" id="stop" name="stop" disabled>Stop</button></div>' +
            '<div style="font-weight:bold; font-size:12px; color:#2d4a6a; border-bottom:1px solid #ccc; padding-bottom:4px; margin-top:14px; margin-bottom:10px;">Layout Settings</div>' +
            '<div class="w2ui-field"><label>Std. Radius:</label><div><input type="text" id="advStandRadius" /></div></div>' +
            '<div class="w2ui-field"><label>Line Width:</label><div><input type="text" id="advLineWidth" /></div></div>' +
            '<div class="w2ui-field"><label>Outer Radius Coeff:</label><div><input type="text" id="advOuterRadiusCoeff" /></div></div>' +
            '<div class="w2ui-field"><label>Inner Radius Coeff:</label><div><input type="text" id="advInnerRadiusCoeff" /></div></div>' +
            '<div class="w2ui-field"><label>Text Offset:</label><div><input type="text" id="advTextOffset" /></div></div>' +
            '<div id="adv-layout-error" style="color:#c0392b; font-size:11px; margin-top:6px; display:none;"></div>' +
            '<div style="display:flex; justify-content:flex-end; gap:8px; margin-top:14px;">' +
            '<button class="w2ui-btn" id="adv-cancel">Cancel</button>' +
            '<button class="w2ui-btn" id="adv-apply">Apply</button>' +
            '</div>' +
            '</div>' +
            '</div>'
        );
        $('#close-advanced-settings').click(function () {
            $('#advanced-settings-overlay').hide();
        });


        $('#loadGraph').on('change', function (event) {
            loadGraph(event);
        });
        $('#loadData').click(function () {
            $('#loadGraph').click();
        });

        //$('#massFactor').w2field('float', { min: 1, max: 10, step: 0.5, arrows: true });
        $('#linkDistance').w2field('float', {min: 0.1, max: 10, step: 0.1, arrows: false});
        $('#linkStrength').w2field('float', {min: 0, max: 1, step: 0.02, arrows: false});
        $('#friction').w2field('float', {min: 0, max: 1, step: 0.02, arrows: false});
        $('#charge').w2field('int', {min: -1000, max: 1000, step: 10, arrows: false});
        // Do not mess with this!
        // $('#chargeDistance').w2field('int', { min: 0, step: 10, arrows: false });
        $('#gravity').w2field('float', {min: 0, max: 1, step: 0.001, arrows: false});
        $('#advStandRadius').w2field('float', {min: 0.1, max: 100, step: 0.5, arrows: false});
        $('#advLineWidth').w2field('float', {min: 0.1, max: 10, step: 0.1, arrows: false});
        $('#advOuterRadiusCoeff').w2field('float', {min: 0.1, max: 5, step: 0.05, arrows: false});
        $('#advInnerRadiusCoeff').w2field('float', {min: 0, max: 5, step: 0.05, arrows: false});
        $('#advTextOffset').w2field('float', {min: 0, max: 50, step: 0.5, arrows: false});

        $('#adv-apply').on('click', function () {
            var newRadius    = parseFloat($('#advStandRadius').val());
            var newLineWidth = parseFloat($('#advLineWidth').val());
            var newOuter     = parseFloat($('#advOuterRadiusCoeff').val());
            var newInner     = parseFloat($('#advInnerRadiusCoeff').val());
            var newTextOffset = parseFloat($('#advTextOffset').val());

            var errors = [];
            if (isNaN(newRadius) || newRadius <= 0)    errors.push('Std. Radius must be > 0.');
            if (isNaN(newLineWidth) || newLineWidth <= 0) errors.push('Line Width must be > 0.');
            if (isNaN(newOuter) || newOuter < 1)       errors.push('Outer Radius Coeff must be \u2265 1.');
            if (isNaN(newInner) || newInner > 1)       errors.push('Inner Radius Coeff must be \u2264 1.');
            if (isNaN(newTextOffset) || newTextOffset < 0) errors.push('Text Offset must be \u2265 0.');

            var $err = $('#adv-layout-error');
            if (errors.length > 0) {
                $err.text(errors.join(' ')).show();
                return;
            }
            $err.hide();

            if (!svg) return;

            // Apply Std. Radius (scale all existing node radii proportionally)
            if (newRadius !== standardRadius) {
                var scale = newRadius / standardRadius;
                standardRadius = newRadius;
                nodeList.forEach(function (node) {
                    node.radius = node.radius * scale;
                    node.proportions.forEach(function (p) { p.radius = p.radius * scale; });
                    node.timeProportions.forEach(function (p) { if (p.radius) p.radius = p.radius * scale; });
                });
            }

            linewidth        = newLineWidth;
            outerRadiusCoeff = newOuter;
            innerRadiusCoeff = newInner;
            textOffset       = newTextOffset;

            updateSVG();
            $('#advanced-settings-overlay').hide();
        });

        $('#adv-cancel').on('click', function () {
            // Restore inputs to current in-effect values and close
            $('#advStandRadius').val(standardRadius);
            $('#advLineWidth').val(linewidth);
            $('#advOuterRadiusCoeff').val(outerRadiusCoeff);
            $('#advInnerRadiusCoeff').val(innerRadiusCoeff);
            $('#advTextOffset').val(textOffset);
            $('#adv-layout-error').hide();
            $('#advanced-settings-overlay').hide();
        });

        $('#help').click(function () {
            $().w2popup({
                url: 'docs/help.html', title: 'tcsBU HELP', width: 800, height: 500,
            });
        });
    } else {
        w2alert('The File APIs are not fully supported by your browser.');
    }

    // Auto-load pre-embedded data files (set by generated {prefix}.js).
    // These globals are defined when the HTML was opened with a data script.
    if (typeof gmlfile !== 'undefined') {
        loadGraph(gmlfile);
        if (typeof groupconffile !== 'undefined') loadGroups(groupconffile);
        if (typeof hapconffile !== 'undefined') loadHaplotypes(hapconffile);
        if (typeof traitconffile !== 'undefined') loadTraits(traitconffile);
    }

});
