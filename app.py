from flask import Flask, request, jsonify
import json
from difflib import get_close_matches

app = Flask(__name__)

# Load lounge database
with open('lounge_data.json', 'r') as f:
    lounge_data = json.load(f)

# Load airport codes
with open('airport_codes.json', 'r') as f:
    airport_codes = json.load(f)

def find_closest_airport(user_input):
    """Fuzzy match airport codes/names"""
    user_input = user_input.upper()
    # Check if exact match exists
    if user_input in airport_codes:
        return user_input
    
    # Check if matches airport code
    matches = get_close_matches(user_input, airport_codes.keys(), n=1, cutoff=0.6)
    if matches:
        return matches[0]
    
    # Check if matches city name
    city_matches = [code for code, city in airport_codes.items() 
                   if user_input.lower() in city.lower()]
    if city_matches:
        return city_matches[0]
    
    return None

def filter_lounges(airport, filters=None):
    """Filter lounges based on criteria"""
    results = [lounge for lounge in lounge_data if lounge['airport_code'] == airport]
    
    if not filters:
        return results
    
    if 'access_method' in filters:
        results = [l for l in results if filters['access_method'] in l['access_methods']]
    
    if 'amenities' in filters:
        results = [l for l in results if all(amenity in l['amenities'] for amenity in filters['amenities'])]
    
    if 'terminal' in filters:
        results = [l for l in results if l['terminal'] == filters['terminal']]
    
    return sorted(results, key=lambda x: x['rating'], reverse=True)

@app.route('/api/find_lounges', methods=['POST'])
def find_lounges():
    data = request.json
    user_input = data.get('query', '').strip()
    
    # Extract airport
    airport = find_closest_airport(user_input)
    if not airport:
        return jsonify({
            "response": "Sorry, I couldn't identify that airport. Please try again with the airport code or city name.",
            "options": []
        })
    
    # Initialize filters
    filters = {}
    
    # Check for access methods in query
    access_keywords = {
        'priority pass': 'Priority Pass',
        'business class': 'Business Class',
        'first class': 'First Class',
        'amex': 'American Express',
        'diners club': 'Diners Club',
        'pay': 'Paid Entry'
    }
    
    for keyword, method in access_keywords.items():
        if keyword in user_input.lower():
            filters['access_method'] = method
            break
    
    # Check for amenities
    amenity_keywords = {
        'shower': 'Showers',
        'wifi': 'Free WiFi',
        'food': 'Hot Food',
        'bar': 'Bar',
        'sleep': 'Sleeping Pods',
        'alcohol': 'Alcohol'
    }
    
    amenities = []
    for keyword, amenity in amenity_keywords.items():
        if keyword in user_input.lower():
            amenities.append(amenity)
    
    if amenities:
        filters['amenities'] = amenities
    
    # Check for terminal
    if 'terminal' in user_input.lower():
        # Simple extraction - would need more robust parsing in production
        parts = user_input.lower().split()
        for i, part in enumerate(parts):
            if part == 'terminal' and i+1 < len(parts):
                filters['terminal'] = parts[i+1].upper()
                break
    
    # Get filtered lounges
    lounges = filter_lounges(airport, filters)
    
    if not lounges:
        return jsonify({
            "response": f"No lounges found at {airport_codes[airport]} matching your criteria.",
            "options": []
        })
    
    # Prepare response
    response = f"Found {len(lounges)} lounges at {airport_codes[airport]}:"
    options = []
    
    for lounge in lounges[:5]:  # Limit to top 5
        options.append({
            "name": lounge['name'],
            "terminal": lounge['terminal'],
            "location": lounge['location'],
            "access": ", ".join(lounge['access_methods']),
            "amenities": ", ".join(lounge['amenities']),
            "hours": lounge['hours'],
            "rating": lounge['rating']
        })
    
    return jsonify({
        "response": response,
        "options": options,
        "airport": airport_codes[airport]
    })

@app.route('/api/lounge_details', methods=['POST'])
def lounge_details():
    data = request.json
    lounge_name = data.get('lounge_name')
    airport = data.get('airport_code')
    
    lounge = next((l for l in lounge_data 
                  if l['name'].lower() == lounge_name.lower() 
                  and l['airport_code'] == airport), None)
    
    if not lounge:
        return jsonify({
            "response": "Sorry, couldn't find details for that lounge.",
            "details": None
        })
    
    details = {
        "description": lounge.get('description', ''),
        "images": lounge.get('images', []),
        "reviews": lounge.get('reviews', []),
        "contact": lounge.get('contact', ''),
        "map_url": lounge.get('map_url', '')
    }
    
    return jsonify({
        "response": f"Here are details for {lounge['name']}:",
        "details": details
    })

if __name__ == '__main__':
    app.run(debug=True)