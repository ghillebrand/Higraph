class VisBlobItem(VisNodeItem):
    # ... existing init ...

    def get_nearest_point_on_path(self, target_point):
        """Finds the closest point on the nodeShape's path to the target_point"""
        # 1. Get the path from the child (rounded rect)
        # Assuming nodeShape is a QGraphicsPathItem or has a path() method
        # If it's a custom item, you may need to recreate the path here:
        path = QPainterPath()
        path.addRoundedRect(self._rect, self.xRadius, self.yRadius)
        
        # 2. Flatten the path into a series of points (polygons)
        # This turns curves into many small straight lines
        polygon = path.toFillPolygon()
        
        nearest_p = QPointF()
        min_dist = float('inf')

        # 3. Iterate through polygon segments to find the closest point
        for i in range(polygon.count()):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % polygon.count()] # Loop back to start
            
            # Find the point on line segment p1-p2 closest to target_point
            curr_nearest = self.closest_point_on_segment(p1, p2, target_point)
            dist = (target_point - curr_nearest).manhattanLength() # Fast approximation
            
            if dist < min_dist:
                min_dist = dist
                nearest_p = curr_nearest
        
        return nearest_p

    def closest_point_on_segment(self, a, b, p):
        """Standard math to find the point on line segment AB closest to point P"""
        ap = p - a
        ab = b - a
        length_sq = ab.x()**2 + ab.y()**2
        if length_sq == 0: return a
        
        # Project P onto AB, clamped between 0 and 1
        t = max(0, min(1, (ap.x() * ab.x() + ap.y() * ab.y()) / length_sq))
        return a + t * ab

    def hoverMoveEvent(self, event):
        if self.hoverHandle:
            # Calculate the point on the rounded border
            nearest_border_point = self.get_nearest_point_on_path(event.pos())
            self.hoverHandle.setPos(nearest_border_point)
            
        super().hoverMoveEvent(event)