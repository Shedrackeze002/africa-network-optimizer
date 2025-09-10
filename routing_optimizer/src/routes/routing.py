 # Load traceroute data
import json
from collections import Counter

with open('hackathon_traceroutes.json', 'r') as f:
    traceroute_data = json.load(f)
print(f"Loaded traceroute_data: {len(traceroute_data)} entries")
if traceroute_data:
    print(f"Sample traceroute_data[0]: {traceroute_data[0]}")

# Prepare all_paths: list of lists of country codes

all_paths = []
for entry in traceroute_data:
    hops = entry.get('hops', [])
    path = [hop.get('country') for hop in hops if hop.get('country')]
    all_paths.append(path)
print(f"Prepared all_paths: {len(all_paths)} paths")
if all_paths:
    print(f"Sample all_paths[0]: {all_paths[0]}")

from collections import defaultdict
# Prepare region pairs and counts
region_pair_counts = Counter()
region_lookup = defaultdict(str)
for entry in traceroute_data:
    hops = entry.get('hops', [])
    if hops:
        origin_country = hops[0].get('country')
        origin_region = hops[0].get('region')
        destination_country = hops[-1].get('country')
        destination_region = hops[-1].get('region')
        if origin_region and destination_region and origin_region not in ['Unknown', 'Unresponsive', 'Private', ''] and destination_region not in ['Unknown', 'Unresponsive', 'Private', '']:
            region_pair_counts[(origin_region, destination_region)] += 1
            region_lookup[(origin_region, destination_region)] = (origin_country, destination_country)

# Prepare invalid hops
invalid_hops = set(['Unknown', 'Unresponsive', 'Private', None, ''])
from flask import Blueprint, request, jsonify
import json
import os

routing_bp = Blueprint('routing', __name__)

# Load the traceroute data (in a real application, this would be from a database)
def load_traceroute_data():
    # Load precomputed summary files for efficient analysis
    country_pairs_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'country_pairs_summary.json')
    hop_data_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'hop_data_summary.json')
    route_paths = []
    try:
        with open(country_pairs_path, 'r', encoding='utf-8') as f:
            country_pairs = json.load(f)
        with open(hop_data_path, 'r', encoding='utf-8') as f:
            hop_data = json.load(f)
        # Patch: Split flat hop list into individual traceroute paths
        # If hop_data contains traceroute/session id, use it; else, split when origin/destination changes
        route_paths = []
        current_path = []
        current_origin = None
        current_destination = None
        for hop in hop_data:
            origin = hop.get('origin_country')
            destination = hop.get('destination_country')
            country = hop.get('country')
            # If origin/destination changes, start a new traceroute path
            if current_origin is None or current_destination is None:
                current_origin = origin
                current_destination = destination
            if origin != current_origin or destination != current_destination:
                if current_path:
                    route_paths.append({'origin': current_origin, 'destination': current_destination, 'path': current_path})
                current_path = []
                current_origin = origin
                current_destination = destination
            current_path.append(country)
        # Add last path
        if current_path:
            route_paths.append({'origin': current_origin, 'destination': current_destination, 'path': current_path})
        return country_pairs, hop_data, route_paths
    except Exception as e:
        print(f"Error loading summary files: {e}")
        return [], [], []

@routing_bp.route('/analyze', methods=['GET'])
def analyze_network():
    from collections import Counter
    # Use loaded data
    # country_pairs: list of (origin, destination) tuples
    # country_pair_counts: dict of (origin, destination) -> count
    # all_paths: list of lists of country codes (the traceroute paths)
    # invalid_hops: set/list of invalid country codes
    top_region_pairs = sorted(region_pair_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_region_pairs_list = [list(pair) for pair, count in top_region_pairs]
    top_region_pairs_counts = {str(list(pair)): count for pair, count in top_region_pairs}

    # Extract top 10 complete routes for each top country pair
    top_routes_per_pair = {}
    for pair in top_region_pairs_list:
        origin, destination = pair
        relevant_routes = []
        for path in all_paths:
            # Remove invalid hops
            valid_path = [hop for hop in path if hop not in invalid_hops]
            if len(valid_path) < 2:
                continue
            # Find all subpaths that start with origin and end with destination, with up to 5 hops in between
            for i in range(len(valid_path)):
                if valid_path[i] != origin:
                    continue
                # Only consider subpaths where destination is after origin
                for j in range(i+2, min(i+8, len(valid_path)+1)):
                    if valid_path[j-1] == destination:
                        # Route must start with origin and end with destination, with up to 5 hops in between
                        route_chain = valid_path[i:j]
                        # Only count if origin and destination are not the same index
                        if route_chain[0] == origin and route_chain[-1] == destination and 2 <= len(route_chain) <= 7:
                            relevant_routes.append(route_chain)
        # Count and sort top 10 routes
        route_counter = Counter(tuple(route) for route in relevant_routes)
        top_10_routes = route_counter.most_common(10)
        top_routes_per_pair[str(pair)] = [list(route) for route, count in top_10_routes]
        print(f"Pair {pair} → {top_region_pairs_counts[str(pair)]}: {len(relevant_routes)} relevant routes found.")
        if len(relevant_routes) == 0:
            print(f"No relevant routes found for pair {pair} → {top_region_pairs_counts[str(pair)]}.")
    top_full_routes = []
    for pair in top_region_pairs_list:
        origin = str(pair[0]) if not isinstance(pair[0], str) else pair[0]
        destination = str(pair[1]) if not isinstance(pair[1], str) else pair[1]
        # Find all routes for this origin-destination region pair
        relevant_routes = []
        for entry in traceroute_data:
            hops = entry.get('hops', [])
            if hops:
                origin_region = hops[0].get('region')
                destination_region = hops[-1].get('region')
                if origin_region == origin and destination_region == destination:
                    path = [hop.get('country') for hop in hops if hop.get('country') and hop.get('country') not in ['Unknown', 'Unresponsive', 'Private', None, '']]
                    relevant_routes.append(path)
        print(f"Region Pair {origin} → {destination}: {len(relevant_routes)} relevant routes found.")
        if not relevant_routes:
            print(f"No relevant routes found for region pair {origin} → {destination}.")
        else:
            # Count frequency of each full chain
            chain_counter = {}
            for r in relevant_routes:
                filtered_path = [str(hop) for hop in r if hop]
                truncated_path = filtered_path[:5]
                chain = [origin] + truncated_path + [destination]
                chain_str = " → ".join(chain)
                chain_counter[chain_str] = chain_counter.get(chain_str, 0) + 1
            # Get up to 10 most frequent chains for this region pair
            top_chains = sorted(chain_counter.items(), key=lambda x: x[1], reverse=True)[:10]
            for chain_str, count in top_chains:
                top_full_routes.append(f"{chain_str} ({count} routes)")
    # Calculate average RTT per country
    rtt_stats = {}
    for entry in traceroute_data:
        for hop in entry.get('hops', []):
            country = hop.get('country')
            rtt = hop.get('rtt')
            if country and rtt is not None and country not in ['Unknown', 'Unresponsive', 'Private', '']:
                if country not in rtt_stats:
                    rtt_stats[country] = {'total_rtt': 0.0, 'hop_count': 0}
                rtt_stats[country]['total_rtt'] += float(rtt)
                rtt_stats[country]['hop_count'] += 1
    high_rtt_countries = []
    for country, stats in rtt_stats.items():
        avg_rtt = stats['total_rtt'] / stats['hop_count'] if stats['hop_count'] > 0 else 0.0
        high_rtt_countries.append({
            'country': country,
            'avg_rtt': avg_rtt,
            'hop_count': stats['hop_count']
        })
    # Sort by avg_rtt descending
    high_rtt_countries = sorted(high_rtt_countries, key=lambda x: x['avg_rtt'], reverse=True)

    # Filter out region pairs with 'Private' or 'Unknown'
    filtered_region_pairs = [pair for pair in top_region_pairs_list if pair[0] not in ['Private', 'Unknown'] and pair[1] not in ['Private', 'Unknown']]
    # Filter out Unknown/Private from top_full_routes
    filtered_routes = []
    for route in top_full_routes:
        route_main = route.split('(')[0].strip()
        hops = [h.strip() for h in route_main.split('→')]
        if any(h in ['Unknown', 'Private'] for h in hops):
            continue
        filtered_routes.append(route)
    # Strategic recommendations using geolocation and city/node names
    from geopy.distance import geodesic
    cable_recommendations = []
    ixp_recommendations = []
    fiber_expansion = []

    # Helper: get city/node and coordinates from hop
    def get_city(hop):
        if hop.get('node_name') and hop.get('node_name') not in ['Unknown Router', 'Private Network', '']:
            return hop['node_name']
        if hop.get('country') and hop.get('region'):
            return f"{hop['country']} ({hop['region']})"
        return None

    def get_coords(hop):
        if hop and hop.get('latitude') is not None and hop.get('longitude') is not None:
            return {'lat': hop['latitude'], 'lon': hop['longitude']}
        return None

    # 1. Submarine Cable Recommendations (use geodesic distance)
    for pair, count in top_region_pairs:
        origin, destination = pair
        # Find representative hops for origin/destination
        origin_hop = None
        dest_hop = None
        for entry in traceroute_data:
            hops = entry.get('hops', [])
            if hops:
                if hops[0].get('region') == origin:
                    origin_hop = hops[0]
                if hops[-1].get('region') == destination:
                    dest_hop = hops[-1]
            if origin_hop and dest_hop:
                break
        # Get coordinates
        origin_coords = (origin_hop['latitude'], origin_hop['longitude']) if origin_hop and origin_hop.get('latitude') and origin_hop.get('longitude') else None
        dest_coords = (dest_hop['latitude'], dest_hop['longitude']) if dest_hop and dest_hop.get('latitude') and dest_hop.get('longitude') else None
        # Calculate geodesic distance
        if origin_coords and dest_coords:
            cable_length = int(geodesic(origin_coords, dest_coords).km)
        else:
            cable_length = 3200
        est_cost = 75_000_000 if cable_length > 4000 else 60_000_000
        avg_rtt = None
        for rtt_entry in high_rtt_countries:
            if rtt_entry['country'] in [origin, destination]:
                avg_rtt = rtt_entry['avg_rtt']
                break
        if avg_rtt is None:
            avg_rtt = 200.0
        rtt_reduction = 0.6 if avg_rtt > 150 else 0.4
        cable_recommendations.append({
            'name': f"{origin} ↔ {destination} Express",
            'endpoints': f"{get_city(origin_hop)} ↔ {get_city(dest_hop)}",
            'origin_coords': get_coords(origin_hop),
            'dest_coords': get_coords(dest_hop),
            'rtt_reduction': int(rtt_reduction * 100),
            'cable_length_km': cable_length,
            'est_cost_usd': est_cost,
            'rationale': f"Direct submarine connection using geolocation; {count} routes analyzed"
        })

    # 2. IXP Recommendations (top cities by RTT)
    city_rtt_counter = Counter()
    city_hop_counter = Counter()
    city_coords = {}
    for entry in traceroute_data:
        for hop in entry.get('hops', []):
            city = get_city(hop)
            if city:
                city_rtt_counter[city] += hop.get('rtt', 0)
                city_hop_counter[city] += 1
                if city not in city_coords and hop.get('latitude') is not None and hop.get('longitude') is not None:
                    city_coords[city] = {'lat': hop['latitude'], 'lon': hop['longitude']}
    top_cities = city_rtt_counter.most_common(5)
    for city, total_rtt in top_cities:
        avg_rtt = total_rtt / city_hop_counter[city] if city_hop_counter[city] else 0
        ixp_recommendations.append({
            'location': city,
            'coords': city_coords.get(city),
            'rationale': f"High average RTT ({avg_rtt:.2f} ms over {city_hop_counter[city]} hops)",
            'tech': "Layer 2 Ethernet, redundant switching, 100Gbps+ core, route servers, traffic monitoring"
        })

    # 3. Terrestrial Fiber Expansion (use geodesic for cross-border)
    for pair, count in top_region_pairs:
        origin, destination = pair
        origin_hop = None
        dest_hop = None
        for entry in traceroute_data:
            hops = entry.get('hops', [])
            if hops:
                if hops[0].get('region') == origin:
                    origin_hop = hops[0]
                if hops[-1].get('region') == destination:
                    dest_hop = hops[-1]
            if origin_hop and dest_hop:
                break
        origin_coords = (origin_hop['latitude'], origin_hop['longitude']) if origin_hop and origin_hop.get('latitude') and origin_hop.get('longitude') else None
        dest_coords = (dest_hop['latitude'], dest_hop['longitude']) if dest_hop and dest_hop.get('latitude') and dest_hop.get('longitude') else None
        if origin_coords and dest_coords:
            fiber_length = int(geodesic(origin_coords, dest_coords).km)
        else:
            fiber_length = 1200
        if origin in ['Eastern Africa', 'Central Africa', 'Western Africa'] and destination in ['Eastern Africa', 'Central Africa', 'Western Africa']:
            fiber_expansion.append({
                'corridor': f"{get_city(origin_hop)} - {get_city(dest_hop)}",
                'impact': f"Improve {origin} to {destination} routing; {count} routes analyzed; Estimated fiber length: {fiber_length} km"
            })

    response = {
        'top_region_pairs': filtered_region_pairs if filtered_region_pairs else [],
        'total_hops_analyzed': sum(len(path) for path in all_paths) if all_paths else 0,
        'top_full_routes': filtered_routes if filtered_routes else [],
        'high_rtt_countries': high_rtt_countries if high_rtt_countries else [],
        'cable_recommendations': cable_recommendations,
        'ixp_recommendations': ixp_recommendations,
        'fiber_expansion': fiber_expansion
    }
    print("API /api/analyze response:", response)
    return jsonify(response)

@routing_bp.route('/optimize', methods=['POST'])
def optimize_routing():
    """Simulate routing optimizations based on proposed infrastructure changes"""
    try:
        data = request.get_json()
        # Get the proposed changes from the request
        proposed_changes = data.get('changes', [])
        # Load original data
        country_pairs, hop_data, route_paths = load_traceroute_data()
        # Simulate the changes (simplified version)
        simulated_improvements = {}
        for change in proposed_changes:
            change_type = change.get('type')
            if change_type == 'new_ixp':
                country = change.get('country')
                improvement_factor = change.get('improvement_factor', 0.5)
                simulated_improvements[country] = {
                    'type': 'IXP',
                    'improvement': f"{(1-improvement_factor)*100:.0f}% RTT reduction",
                    'estimated_cost': change.get('cost', 'Not specified')
                }
            elif change_type == 'new_cable':
                source = change.get('source_country')
                destination = change.get('destination_country')
                new_rtt = change.get('new_rtt', 10)
                simulated_improvements[f"{source}-{destination}"] = {
                    'type': 'Submarine Cable',
                    'improvement': f"Direct link with {new_rtt}ms RTT",
                    'estimated_cost': change.get('cost', 'Not specified')
                }
        expected_benefits = [
            f"Reduced latency for {len(hop_data)} hops and {len(route_paths)} routes",
            "Improved redundancy and reliability",
            "Enhanced economic opportunities through better connectivity"
        ]
        return jsonify({
            'original_analysis': {
                'total_routes': len(country_pairs),
                'total_hops': len(hop_data)
            },
            'proposed_improvements': simulated_improvements,
            'expected_benefits': expected_benefits
        })
    except Exception as e:
        return jsonify({'error': f'Failed to run optimization: {str(e)}'}), 500

@routing_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    """Generate infrastructure recommendations based on actual analysis results"""
    try:
        country_pairs, hop_data, route_paths = load_traceroute_data()
        recommendations = []
        total_investment = 0
        # Top 3 country pairs for infrastructure focus
        for idx, (pair, count) in enumerate(country_pairs[:3]):
            src, dst = pair
            recommendations.append({
                'priority': 'High' if idx == 0 else 'Medium',
                'type': 'Traffic Infrastructure',
                'route': f'{src} ↔ {dst}',
                'rationale': f'Top traffic pair ({count} routes) between {src} and {dst}',
                'estimated_impact': f'{60-idx*10}% reduction in RTT',
                'estimated_cost': f'${3+idx*10} million USD'
            })
            total_investment += (3+idx*10)
        # Analyze countries with highest RTT
        country_rtt = {}
        country_rtt_counts = {}
        for hop in hop_data:
            country = hop['country']
            rtt = hop['rtt']
            country_rtt[country] = country_rtt.get(country, 0) + rtt
            country_rtt_counts[country] = country_rtt_counts.get(country, 0) + 1
        avg_rtt_per_country = []
        for country, total_rtt in country_rtt.items():
            count = country_rtt_counts[country]
            if count > 10:
                avg_rtt_per_country.append({
                    'country': country,
                    'avg_rtt': total_rtt / count,
                    'hop_count': count
                })
        avg_rtt_per_country.sort(key=lambda x: x['avg_rtt'], reverse=True)
        # Recommend improvements for top 3 high RTT countries
        for idx, country_info in enumerate(avg_rtt_per_country[:3]):
            country = country_info['country']
            avg_rtt = country_info['avg_rtt']
            recommendations.append({
                'priority': 'High' if idx == 0 else 'Medium',
                'type': 'RTT Optimization',
                'location': country,
                'rationale': f'{country} has high average RTT ({avg_rtt:.2f} ms over {country_info["hop_count"]} hops)',
                'estimated_impact': f'{70-idx*10}% reduction in RTT',
                'estimated_cost': f'${5+idx*10} million USD'
            })
            total_investment += (5+idx*10)
        # Social impact based on analysis size
        social_impact = [
            f'Improved access to digital services for {len(hop_data)} hops',
            'Enhanced educational opportunities',
            'Better healthcare connectivity',
            'Increased economic opportunities'
        ]
        return jsonify({
            'recommendations': recommendations,
            'total_estimated_investment': f'${total_investment} million USD',
            'expected_roi_timeline': '3-5 years',
            'social_impact': social_impact
        })
    except Exception as e:
        return jsonify({'error': f'Failed to generate recommendations: {str(e)}'}), 500

