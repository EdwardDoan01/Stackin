from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import ChatMessage, ChatbotSuggestion
from .serializers import ChatMessageSerializer, ChatbotSuggestionSerializer, ChatbotMessageSerializer
import uuid
import re

class ChatbotMessageView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ChatbotMessageSerializer(data=request.data)
        if serializer.is_valid():
            message = serializer.validated_data['message']
            session_id = serializer.validated_data.get('session_id', str(uuid.uuid4()))
            
            # Generate AI response
            response = self.generate_ai_response(message, request.user)
            
            # Save to database
            chat_message = ChatMessage.objects.create(
                user=request.user if request.user.is_authenticated else None,
                message=message,
                response=response,
                session_id=session_id
            )
            
            return Response({
                'response': response,
                'session_id': session_id,
                'message_id': chat_message.id
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def generate_ai_response(self, user_input, user):
        """Generate AI response based on user input"""
        input_lower = user_input.lower()
        
        # Greeting responses
        if any(word in input_lower for word in ['xin chào', 'hello', 'hi', 'chào']):
            return 'Xin chào! Tôi là AI Assistant của Stackin. Tôi có thể giúp bạn tìm hiểu về các dịch vụ, hướng dẫn sử dụng, hoặc trả lời các câu hỏi về nền tảng. Bạn cần hỗ trợ gì?'
        
        # Service-related questions
        if any(word in input_lower for word in ['dịch vụ', 'service', 'làm gì', 'có gì']):
            return '''Stackin cung cấp nhiều dịch vụ như:
• Lắp ráp đồ nội thất
• Di chuyển đồ đạc  
• Lắp đặt đồ vật
• Sửa chữa nhà cửa
• Dọn dẹp nhà
• Hỗ trợ IT

Bạn quan tâm đến dịch vụ nào? Tôi có thể hướng dẫn chi tiết hơn.'''
        
        # Pricing questions
        if any(word in input_lower for word in ['giá', 'price', 'chi phí', 'tiền', 'bao nhiêu']):
            return '''Giá dịch vụ của Stackin rất cạnh tranh và minh bạch:

• Mỗi dịch vụ có mức giá khác nhau tùy theo độ phức tạp
• Giá được hiển thị rõ ràng trên từng task
• Bạn có thể thương lượng trực tiếp với Tasker
• Thanh toán an toàn qua hệ thống escrow

Bạn muốn tìm hiểu về giá của dịch vụ nào cụ thể?'''
        
        # How to use platform
        if any(word in input_lower for word in ['cách sử dụng', 'hướng dẫn', 'how to', 'làm sao']):
            return '''Để sử dụng Stackin rất đơn giản:

1️⃣ **Đăng ký tài khoản** - Tạo tài khoản miễn phí
2️⃣ **Đăng task** - Mô tả công việc cần làm
3️⃣ **Chọn Tasker** - Xem profile và chọn người phù hợp
4️⃣ **Thanh toán** - Trả tiền qua escrow (an toàn)
5️⃣ **Hoàn thành** - Tasker thực hiện công việc
6️⃣ **Xác nhận** - Kiểm tra và đánh giá

Bạn có cần hướng dẫn chi tiết bước nào không?'''
        
        # Tasker registration
        if any(word in input_lower for word in ['trở thành tasker', 'tasker', 'kiếm tiền', 'làm tasker']):
            return '''Để trở thành Tasker và kiếm tiền trên Stackin:

📋 **Yêu cầu:**
• Trên 18 tuổi
• Có giấy tờ tùy thân hợp lệ
• Có kỹ năng trong lĩnh vực dịch vụ

🚀 **Quy trình đăng ký:**
1. Đăng ký tài khoản
2. Điền thông tin cá nhân
3. Upload giấy tờ tùy thân
4. Chọn kỹ năng và dịch vụ
5. Chờ xét duyệt (1-3 ngày)
6. Bắt đầu nhận task và kiếm tiền!

Bạn muốn bắt đầu đăng ký Tasker không?'''
        
        # Payment questions
        if any(word in input_lower for word in ['thanh toán', 'payment', 'tiền', 'escrow']):
            return '''Hệ thống thanh toán Stackin rất an toàn:

🔒 **Escrow System:**
• Tiền được giữ trong ví escrow
• Chỉ release khi task hoàn thành
• Bảo vệ cả Client và Tasker

💳 **Phương thức thanh toán:**
• Thẻ tín dụng/ghi nợ
• Chuyển khoản ngân hàng
• Ví điện tử

✅ **Quy trình:**
1. Client thanh toán → Escrow
2. Tasker hoàn thành task
3. Client xác nhận → Release tiền
4. Tasker nhận tiền

Bạn có thắc mắc gì về thanh toán không?'''
        
        # Support questions
        if any(word in input_lower for word in ['hỗ trợ', 'support', 'giúp đỡ', 'liên hệ']):
            return '''Tôi luôn sẵn sàng hỗ trợ bạn! 

📞 **Cách liên hệ:**
• Chat trực tiếp với tôi (AI Assistant)
• Email: support@stackin.com
• Hotline: 1900-xxxx
• Sử dụng chức năng "Báo cáo" trên trang

🆘 **Hỗ trợ 24/7:**
• Câu hỏi về dịch vụ
• Vấn đề kỹ thuật
• Tranh chấp
• Hướng dẫn sử dụng

Bạn đang gặp vấn đề gì? Tôi sẽ giúp bạn giải quyết!'''
        
        # Default response
        return f'''Cảm ơn bạn đã hỏi về: "{user_input}"

Tôi hiểu bạn đang quan tâm đến chủ đề này. Để tôi có thể hỗ trợ tốt hơn, bạn có thể hỏi về:

🔍 **Các chủ đề phổ biến:**
• Dịch vụ của Stackin
• Cách sử dụng nền tảng  
• Giá cả và thanh toán
• Trở thành Tasker
• Hỗ trợ kỹ thuật

Hoặc bạn có thể hỏi cụ thể hơn để tôi hỗ trợ chính xác nhất! 😊'''

class ChatbotSuggestionsView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        suggestions = ChatbotSuggestion.objects.filter(is_active=True)
        serializer = ChatbotSuggestionSerializer(suggestions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)