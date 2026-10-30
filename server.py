"""Small local demo server. Python 3.10+, no third-party dependencies."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path
import os, json

ROOT = Path(__file__).resolve().parent
ALLOWED = ['KPI','Trend','Insight','Audience','Channels','Schedule','Slider','Capacity','Constraint','Region','Action']
SCHEMA = {
  'type':'object','additionalProperties':False,'required':['intent','title','reason','components'],
  'properties':{
    'intent':{'type':'string'},'title':{'type':'string'},'reason':{'type':'string'},
    'components':{'type':'array','minItems':1,'maxItems':12,'items':{
      'type':'object','additionalProperties':False,
      'required':['type','title','value','detail','text','values','min','max','action'],
      'properties':{
        'type':{'type':'string','enum':ALLOWED},'title':{'type':'string'},
        'value':{'type':['string','number','null']},'detail':{'type':['string','null']},
        'text':{'type':['string','null']},'values':{'type':['array','null'],'items':{'type':'number'}},
        'min':{'type':['number','null']},'max':{'type':['number','null']},
        'action':{'type':['string','null'],'enum':['preview',None]}
      }
    }}
  }
}
SYSTEM = '''You are a UI composition planner for a self-contained educational demo for outbound campaign managers. Choose the most appropriate component STRUCTURE for the user's task. Do not merely change values in a fixed template. Follow-up requests can extend or replace the existing composition. Output a valid JSON spec complying with the provided JSON schema. Allowed component types: KPI (value/detail), Trend (values list of 5 numbers), Insight (text), Audience (value numeric), Channels, Schedule, Slider (value/min/max numbers), Capacity, Constraint (value numeric), Region (value string), Action (action preview). Every component must have all fields; use null for unused optional fields. Values are illustrative. Make actions always review-only. Never claim real customer data, real APIs, genuine compliance enforcement, or accurate staffing forecasting. Use a concise reason describing composition choice. Use at most 7 components. When user requests a what-if simulation include Slider and Capacity. When user asks new campaign include Audience/Channels/Schedule/Action. When user mentions EU or abandonment limits include Region and Constraint. Do not place user supplied text into code or script.''' 

DEEPSEEK_FORMAT = '''
Return JSON only, no markdown. The JSON must match this JSON schema exactly; every top-level field and every component field is required (use null for unused ones):
'''+json.dumps(SCHEMA)+'''
Example: {"intent":"build","title":"Re-engagement campaign","reason":"...","components":[{"type":"Audience","title":"Audience","value":2000,"detail":null,"text":null,"values":null,"min":null,"max":null,"action":null},{"type":"Action","title":"Review campaign","value":null,"detail":null,"text":null,"values":null,"min":null,"max":null,"action":"preview"}]}'''

def validate(spec):
    if not isinstance(spec,dict) or not isinstance(spec.get('components'),list) or not 1 <= len(spec['components']) <= 12:
        raise ValueError('Invalid components')
    if not isinstance(spec.get('title'),str) or len(spec['title'])>120: raise ValueError('Invalid title')
    for c in spec['components']:
        if not isinstance(c,dict) or c.get('type') not in ALLOWED: raise ValueError('Unsupported component')
        if not isinstance(c.get('title'),str) or len(c['title'])>120: raise ValueError('Invalid component title')
        if c.get('action') not in [None,'preview']: raise ValueError('Forbidden action')
        if c.get('values') is not None and (not isinstance(c['values'],list) or len(c['values'])>30): raise ValueError('Invalid trend data')
    return spec

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def respond(self,status,obj):
        body=json.dumps(obj).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_POST(self):
        if self.path!='/api/compose': return self.respond(404,{'error':'Not found'})
        provider=os.getenv('AI_PROVIDER', 'deepseek' if os.getenv('DEEPSEEK_API_KEY') else 'openai').lower()
        if provider not in ('openai','deepseek'):return self.respond(400,{'error':'AI_PROVIDER must be openai or deepseek'})
        key=os.getenv('DEEPSEEK_API_KEY' if provider=='deepseek' else 'OPENAI_API_KEY','')
        if not key:return self.respond(503,{'error':f'API key not set for {provider}. Use scripted mode or set the corresponding environment variable.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>25000:raise ValueError('Request size invalid')
            data=json.loads(self.rfile.read(length))
            prompt=data.get('prompt','')
            if not isinstance(prompt,str) or not 1<=len(prompt)<=4000:raise ValueError('Prompt must be 1-4000 characters')
            previous=data.get('previous_spec')
            previous=json.dumps(previous,ensure_ascii=False)[:9000] if previous else 'none'
            user_input='User request: '+prompt+'\nExisting UI spec: '+previous+'\nSynthetic context: 12400 contacts, 34% answer rate, 8.2% conversion rate, 24 agents.'
            if provider=='deepseek':
                body={'model':os.getenv('DEEPSEEK_MODEL','deepseek-chat'),
                      'messages':[{'role':'system','content':SYSTEM+DEEPSEEK_FORMAT},
                                  {'role':'user','content':user_input}],
                      'response_format':{'type':'json_object'},'stream':False,'max_tokens':3000}
                api_url='https://api.deepseek.com/chat/completions'
            else:
                body={'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),'instructions':SYSTEM,'input':user_input,
                      'text':{'format':{'type':'json_schema','name':'ui_spec','strict':True,'schema':SCHEMA}},'store':False}
                api_url='https://api.openai.com/v1/responses'
            request=Request(api_url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+key},method='POST')
            with urlopen(request,timeout=60) as resp: result=json.load(resp)
            if provider=='deepseek':
                text=result.get('choices',[{}])[0].get('message',{}).get('content') or ''
            else:
                text=''.join(part.get('text','') for output in result.get('output',[]) for part in output.get('content',[]) if part.get('type')=='output_text')
            if not text:raise ValueError('Model did not return a UI specification')
            spec=validate(json.loads(text));return self.respond(200,{'spec':spec})
        except HTTPError as e:
            try: detail=json.loads(e.read()).get('error',{}).get('message','API error')
            except Exception: detail='API error'
            return self.respond(502,{'error':str(detail)[:400]})
        except Exception as e:return self.respond(400,{'error':str(e)[:400]})

if __name__=='__main__':
    port=int(os.getenv('PORT','8765'))
    print(f'Intelligent UI Lab at http://localhost:{port} | live AI '+('enabled' if (os.getenv('OPENAI_API_KEY') or os.getenv('DEEPSEEK_API_KEY')) else 'disabled'))
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
