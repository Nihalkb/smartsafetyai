from app import db
from models import SafetyProtocol
from datetime import datetime, timedelta
import random

def load_sample_protocols():
    """Load sample safety protocols for demonstration purposes"""
    protocols = [
        {
            'title': 'Emergency Response to Hazardous Material Spills',
            'category': 'Hazardous Materials',
            'content': '''
            1. EVACUATE the immediate area of personnel.
            2. IDENTIFY the spilled material from a safe distance using identification placards or shipping documents.
            3. ISOLATE the spill area and DENY entry to unauthorized personnel.
            4. NOTIFY emergency response personnel and your supervisor.
            5. CONTAIN the spill if it is safe to do so, using appropriate PPE and containment materials.
            6. FOLLOW decontamination procedures after the incident.
            7. DOCUMENT the incident including materials, quantity, response actions, and outcomes.
            
            For chemical spills:
            - Use appropriate neutralization agents depending on the chemical type
            - Do not attempt to clean up unknown materials
            - Consult the SDS (Safety Data Sheet) for specific handling instructions
            ''',
            'keywords': 'hazmat,spill,chemical,emergency,containment'
        },
        {
            'title': 'Pipeline Pressure Relief Procedures',
            'category': 'Pipeline Operations',
            'content': '''
            When pipeline pressure exceeds maximum operating pressure (MOP):
            
            1. Monitor pressure gauges and automated alerts closely.
            2. Identify the source of excess pressure.
            3. Activate pressure relief systems if pressure continues to rise.
            4. Notify control center immediately.
            5. Reduce input flow rates to affected pipeline segment.
            6. Open bypass or alternate flow paths if available.
            7. Prepare for controlled release through designated relief points if necessary.
            8. Document all actions taken and record pressure readings at 5-minute intervals.
            9. Once pressure is stabilized, conduct visual inspection of affected pipeline segments.
            10. Complete incident report and assessment of relief valve operation.
            
            NEVER attempt to manually override pressure relief valves without proper authorization.
            ''',
            'keywords': 'pipeline,pressure,relief,valve,MOP,safety'
        },
        {
            'title': 'Gas Leak Detection and Response',
            'category': 'Gas Safety',
            'content': '''
            Detecting and Responding to Gas Leaks:
            
            Detection Methods:
            - Use calibrated gas detection equipment during regular inspections
            - Recognize the odor of mercaptan (rotten egg smell) added to natural gas
            - Watch for visual indicators: dead vegetation, bubbling in standing water, or dust blowing from ground
            - Monitor for hissing sounds near gas equipment or pipelines
            
            Response Procedure:
            1. If detection equipment alarms, evacuate the area immediately.
            2. Do NOT create ignition sources (no smoking, electrical switches, cell phones, vehicles).
            3. From a safe location, call the emergency response team.
            4. Secure the area to prevent access.
            5. Shut off gas supply if it is safe to do so and you are authorized.
            6. Allow ventilation of enclosed spaces before re-entry.
            7. Follow atmospheric testing protocols before declaring the area safe.
            
            All suspected leaks must be reported regardless of size or confirmation.
            ''',
            'keywords': 'gas,leak,detection,evacuation,mercaptan'
        },
        {
            'title': 'Emergency Evacuation Procedure',
            'category': 'General Safety',
            'content': '''
            When evacuation is necessary:
            
            1. Remain calm and proceed to the nearest safe exit.
            2. If safe to do so, alert others in your immediate area.
            3. DO NOT use elevators during fire evacuations.
            4. Take emergency kit if readily available, but DO NOT delay evacuation.
            5. If smoke is present, stay low and cover mouth/nose with a cloth.
            6. Feel doors before opening - if hot, find alternate route.
            7. Proceed to designated assembly points and check in with your supervisor.
            8. Report any missing persons to emergency responders.
            9. Do not re-enter the building until authorized by emergency personnel.
            
            Evacuation wardens should sweep their assigned areas if safe to do so.
            Review evacuation maps regularly and know at least two exit routes from your work area.
            ''',
            'keywords': 'evacuation,emergency,assembly,fire,safety'
        },
        {
            'title': 'Personal Protective Equipment (PPE) Requirements',
            'category': 'Personal Safety',
            'content': '''
            Minimum PPE Requirements for Field Operations:
            
            1. Head Protection: ANSI-approved hard hat in good condition, properly adjusted.
            2. Eye Protection: Safety glasses with side shields meeting ANSI Z87.1 standards.
            3. Hand Protection: Cut-resistant gloves appropriate for the task.
            4. Foot Protection: Steel-toed boots meeting ASTM F2413 standards.
            5. Flame-Resistant Clothing: FR coveralls or shirt/pants when working near potential ignition sources.
            6. High-Visibility Clothing: Class 2 high-visibility vest or clothing when working near roadways.
            
            Task-Specific PPE:
            - Hearing protection when noise levels exceed 85 dBA
            - Respiratory protection when air quality is compromised
            - Fall protection when working at heights above 6 feet
            - Face shields when grinding, cutting, or handling chemicals
            - Chemical-resistant clothing when handling hazardous materials
            
            All PPE must be inspected before each use and maintained in good condition.
            Damaged PPE must be replaced immediately.
            ''',
            'keywords': 'PPE,safety,protective,equipment,gear'
        },
        {
            'title': 'Confined Space Entry Protocol',
            'category': 'High-Risk Operations',
            'content': '''
            Before entering any confined space:
            
            1. Obtain and complete a Confined Space Entry Permit.
            2. Verify that all mechanical isolation is complete.
            3. Test the atmosphere for oxygen content, flammable gases, and potential toxic air contaminants.
            4. Continuous atmosphere monitoring is required throughout the duration of entry.
            5. Establish retrieval systems and rescue procedures.
            6. Assign a trained attendant to remain outside the confined space.
            7. Use appropriate PPE based on hazard assessment.
            8. Maintain communication between entrant and attendant at all times.
            9. Terminate entry and evacuate if hazardous conditions develop.
            
            Oxygen levels must be between 19.5% and 23.5%.
            Flammable gases must be below 10% of Lower Explosive Limit (LEL).
            Toxic contaminants must be below their respective Permissible Exposure Limits (PELs).
            
            NEVER enter a confined space without proper authorization and verification of safe conditions.
            ''',
            'keywords': 'confined space,permit,entry,atmospheric testing,isolation'
        },
        {
            'title': 'Fire Prevention and Response',
            'category': 'Fire Safety',
            'content': '''
            Fire Prevention:
            
            1. Maintain good housekeeping: keep workspaces free of unnecessary combustible materials.
            2. Inspect electrical equipment regularly for damage.
            3. Store flammable liquids in approved containers away from ignition sources.
            4. Maintain clearance around fire suppression equipment and electrical panels.
            5. Follow hot work permit procedures for all cutting, welding, and grinding operations.
            6. Dispose of oily rags in approved metal containers with self-closing lids.
            
            Fire Response:
            
            1. Activate the nearest fire alarm and call emergency services.
            2. Attempt to extinguish only small, incipient fires if trained and safe to do so.
            3. For Class A fires (ordinary combustibles): Use water or ABC extinguishers.
            4. For Class B fires (flammable liquids): Use BC or ABC extinguishers, NEVER water.
            5. For Class C fires (electrical equipment): Use BC or ABC extinguishers, NEVER water.
            6. For Class D fires (combustible metals): Use only Class D extinguishers.
            7. If fire cannot be controlled, evacuate immediately.
            
            Remember PASS method for extinguisher use:
            Pull the pin, Aim at the base of fire, Squeeze the handle, Sweep side to side.
            ''',
            'keywords': 'fire,extinguisher,prevention,response,PASS'
        },
        {
            'title': 'Hydrogen Sulfide (H2S) Safety',
            'category': 'Toxic Substances',
            'content': '''
            Hydrogen Sulfide (H2S) Safety Protocol:
            
            Properties and Hazards:
            - Colorless gas with "rotten egg" odor at low concentrations
            - Heavier than air, accumulates in low-lying areas
            - Extremely toxic and flammable
            - Causes olfactory fatigue (loss of smell) at higher concentrations
            
            Safety Measures:
            1. Personal H2S monitors must be worn at all times in potential H2S areas.
            2. Calibrate and bump test H2S monitors before each use.
            3. Wind socks or flags must be visible to indicate wind direction for escape.
            4. Work upwind of potential H2S sources whenever possible.
            5. Always work with a partner in areas with potential H2S exposure.
            
            Emergency Response:
            1. If alarm sounds (10 ppm or higher), evacuate immediately upwind or crosswind.
            2. If performing rescue, wear positive pressure SCBA.
            3. Move affected persons to fresh air.
            4. Begin CPR if victim is not breathing.
            5. Seek immediate medical attention even if symptoms resolve.
            
            Exposure symptoms: headache, dizziness, nausea, eye irritation, unconsciousness, death.
            H2S can be fatal at concentrations of 100 ppm or higher.
            ''',
            'keywords': 'H2S,hydrogen sulfide,toxic gas,rotten egg,sulfur'
        }
    ]
    
    # Create protocols with varying dates
    now = datetime.now()
    for i, protocol_data in enumerate(protocols):
        # Generate date between 30-730 days ago
        days_ago = random.randint(30, 730)
        protocol_date = now - timedelta(days=days_ago)
        
        protocol = SafetyProtocol(
            title=protocol_data['title'],
            category=protocol_data['category'],
            content=protocol_data['content'],
            keywords=protocol_data['keywords'],
            date_added=protocol_date
        )
        db.session.add(protocol)
    
    db.session.commit()
