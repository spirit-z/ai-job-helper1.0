import os,json,base64,cgi,io,urllib.request
from http.server import BaseHTTPRequestHandler

SYSTEM="""你是AI求职顾问。用户没有AI/半导体等垂直经验，正在寻找能进入AI/AIGC、SaaS、半导体、企业服务等行业的可迁移岗位。她不喜欢纯电话销售、每天大量陌生电话、卖课、收费入职。
直接理解上传的BOSS截图。多张截图若属于同一岗位要合并；不同岗位分别输出。不要编造工商信息；无法核查就写未核实。不要仅凭社保人数等单项指标判定骗子。
recommendation只能是投、先问HR、跳过；score为0-100。只输出JSON。"""

def imgdata(raw,mime):
    return "data:%s;base64,%s"%(mime,base64.b64encode(raw).decode())

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            n=int(self.headers.get("content-length","0")); body=self.rfile.read(n)
            env={"REQUEST_METHOD":"POST","CONTENT_TYPE":self.headers.get("content-type",""),"CONTENT_LENGTH":str(n)}
            fs=cgi.FieldStorage(fp=io.BytesIO(body),headers=self.headers,environ=env)
            vals=fs["images"] if "images" in fs else []
            if not isinstance(vals,list): vals=[vals]
            content=[{"type":"text","text":"""分析这些BOSS岗位截图，返回：
{"jobs":[{"job_title":"","company":"","score":0,"recommendation":"投|先问HR|跳过","fit_reasons":[],"risks":[],"company_check":"","personal_fit":"","hr_question":"","message":""}]}"""}]
            for x in vals:
                content.append({"type":"image_url","image_url":{"url":imgdata(x.file.read(),x.type or "image/jpeg")}})
            key=os.environ.get("ARK_API_KEY")
            if not key: raise Exception("Vercel尚未配置 ARK_API_KEY")
            model=os.environ.get("ARK_MODEL","doubao-seed-2.1-pro")
            payload={"model":model,"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":content}],"temperature":0.2,"max_tokens":3000}
            req=urllib.request.Request("https://ark.cn-beijing.volces.com/api/v3/chat/completions",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json","Authorization":"Bearer "+key})
            with urllib.request.urlopen(req,timeout=120) as r: ans=json.loads(r.read().decode())
            text=ans["choices"][0]["message"]["content"].strip()
            if text.startswith("```"):
                text=text.strip("`").strip()
                if text.startswith("json"): text=text[4:].strip()
            data=json.loads(text)
            self.send_response(200);self.send_header("Content-Type","application/json; charset=utf-8");self.end_headers();self.wfile.write(json.dumps(data,ensure_ascii=False).encode())
        except Exception as e:
            self.send_response(500);self.send_header("Content-Type","application/json; charset=utf-8");self.end_headers();self.wfile.write(json.dumps({"error":str(e)},ensure_ascii=False).encode())
